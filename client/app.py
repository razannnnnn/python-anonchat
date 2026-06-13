import asyncio
import json
import time as time_module
from textual.app import App, ComposeResult
from textual.widgets import Input, RichLog, Label, ListView, ListItem
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual import work
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.events import Key
import websockets
import re

from config import COLORS, CSS, MAX_MSG_BUFFER, MAX_HISTORY
from message_handler import process_server_message
from commands import process_user_command, process_chat_message

class ChatApp(App):
    CSS = CSS
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+u", "toggle_sidebar", "Users", show=True),
    ]

    my_username: reactive[str] = reactive("")
    current_room: reactive[str] = reactive("global")
    room_password: str = ""
    online_count: reactive[int] = reactive(0)
    online_users: list = []
    ws = None
    connected = False
    username_submitted = False
    in_chat = False
    websocket_url = ""

    # ── New state ──
    sent_history: list = []
    history_index: int = -1
    history_temp: str = ""
    last_whisper_from: str = ""
    sidebar_visible: bool = True
    ping_ms: int = -1
    _reconnect_task = None
    _ping_task = None

    # Message buffer for self-destruct
    _msg_buffer: list = []  # list of {"id": int, "text": str}
    _msg_counter: int = 0
    _burn_tasks: dict = {}  # {msg_id: asyncio.Task}

    def __init__(self, url: str):
        super().__init__()
        self.websocket_url = url

    def compose(self) -> ComposeResult:
        with Vertical(id="username-screen"):
            with Vertical(id="username-box"):
                yield Label("◈ ANON CHAT", id="username-title")
                yield Label("Masukkan username atau kosongkan untuk random", id="username-subtitle")
                yield Input(placeholder="Username...", id="username-input")

    def on_mount(self) -> None:
        self.title = "Anon Chat"
        self.sent_history = []
        self.online_users = []
        self._msg_buffer = []
        self._burn_tasks = {}
        self.query_one("#username-input").focus()
        if self.websocket_url:
            self.connect_ws()
        else:
            self.notify("URL tidak diberikan!", severity="error")

    @work(exclusive=True, thread=False)
    async def connect_ws(self):
        backoff = 1
        max_backoff = 30
        while True:
            try:
                async with websockets.connect(self.websocket_url) as ws:
                    self.ws = ws
                    self.connected = True
                    backoff = 1  # reset on success
                    self.update_status_bar()
                    # Start ping worker
                    self.start_ping_worker()

                    async for raw in ws:
                        data = json.loads(raw)
                        await process_server_message(self, data)

            except Exception as e:
                self.connected = False
                self.ws = None
                self.ping_ms = -1
                self.update_status_bar()

                if self.in_chat:
                    self.append_system(f"⚠ Koneksi terputus: {e}")
                    self.append_system(f"↻ Mencoba menghubungkan ulang dalam {backoff}d...")

                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

                if self.in_chat:
                    self.append_system("↻ Menghubungkan ulang...")
                    # Re-send username on reconnect
                    self.username_submitted = False

    def start_ping_worker(self):
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
        self._ping_task = asyncio.ensure_future(self._ping_loop())

    async def _ping_loop(self):
        """Measure WebSocket latency every 10 seconds."""
        try:
            while self.ws and self.connected:
                try:
                    start = time_module.monotonic()
                    pong = await self.ws.ping()
                    await asyncio.wait_for(pong, timeout=5)
                    elapsed = (time_module.monotonic() - start) * 1000
                    self.ping_ms = int(elapsed)
                except asyncio.TimeoutError:
                    self.ping_ms = -1
                except Exception:
                    self.ping_ms = -1
                    break
                self.update_status_bar()
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            pass

    def render_chat_message(self, sender: str, text: str, time_str: str, is_me: bool):
        # Check for burn prefix
        burn_match = re.match(r"^\[\[BURN:(\d+)\]\]\s*(.*)$", text)
        burn_seconds = 0
        if burn_match:
            burn_seconds = int(burn_match.group(1))
            text = burn_match.group(2)

        # Check for @mention
        has_mention = False
        if self.my_username and not is_me:
            pattern = re.compile(re.escape(f"@{self.my_username}"), re.IGNORECASE)
            if pattern.search(text):
                has_mention = True
                # Highlight the mention
                text = pattern.sub(f"[{COLORS['mention']}]@{self.my_username}[/{COLORS['mention']}]", text)

        if has_mention:
            self.bell()

        # Build the display line
        color = COLORS["self"] if is_me else COLORS["other"]
        suffix = " [dim](kamu)[/dim]" if is_me else ""
        time_part = f"[{COLORS['time']}]{time_str}[/{COLORS['time']}]" if time_str else ""

        if burn_seconds > 0:
            burn_tag = f" [{COLORS['burn']}]🔥{burn_seconds}d[/{COLORS['burn']}]"
        else:
            burn_tag = ""

        mention_prefix = "🔔 " if has_mention else ""
        line = f"{mention_prefix}{time_part} [{color}]{sender}{suffix}[/{color}]{burn_tag} › {text}"

        msg_id = self._write_msg(line)

        if burn_seconds > 0 and msg_id is not None:
            task = asyncio.ensure_future(self._burn_message(msg_id, burn_seconds))
            self._burn_tasks[msg_id] = task

    async def _burn_message(self, msg_id: int, seconds: int):
        """Remove a message from the chat log after `seconds` seconds."""
        await asyncio.sleep(seconds)
        # Remove from buffer and re-render
        self._msg_buffer = [m for m in self._msg_buffer if m["id"] != msg_id]
        if msg_id in self._burn_tasks:
            del self._burn_tasks[msg_id]
        self._rerender_chat()

    def _write_msg(self, line: str) -> int:
        """Write a message to chat log and track it for burn support. Returns msg_id."""
        try:
            log = self.query_one("#chat-log", RichLog)
            log.write(line)
            self._msg_counter += 1
            msg_id = self._msg_counter
            self._msg_buffer.append({"id": msg_id, "text": line})
            # Trim buffer if too large
            if len(self._msg_buffer) > MAX_MSG_BUFFER:
                self._msg_buffer = self._msg_buffer[-MAX_MSG_BUFFER:]
            return msg_id
        except NoMatches:
            return None

    def _rerender_chat(self):
        """Clear and re-render all messages in the buffer."""
        try:
            log = self.query_one("#chat-log", RichLog)
            log.clear()
            for msg in self._msg_buffer:
                log.write(msg["text"])
        except NoMatches:
            pass

    def append_whisper_in(self, sender: str, text: str, time_str: str):
        time_part = f"[{COLORS['time']}]{time_str}[/{COLORS['time']}] " if time_str else ""
        line = f"🔔 {time_part}[{COLORS['whisper']}][DM ← {sender}][/{COLORS['whisper']}] › {text}"
        self._write_msg(line)
        self.bell()

    def append_whisper_out(self, target: str, text: str, time_str: str):
        time_part = f"[{COLORS['time']}]{time_str}[/{COLORS['time']}] " if time_str else ""
        line = f"{time_part}[{COLORS['whisper']}][DM → {target}][/{COLORS['whisper']}] › {text}"
        self._write_msg(line)

    def switch_to_chat(self):
        self.in_chat = True
        try:
            self.query_one("#username-screen").remove()
        except NoMatches:
            pass

        header = Horizontal(
            Label("◈ ROOM:", id="room-label"),
            Label(f"#{self.current_room}", id="room-name-label"),
            Label(" 👤", id="user-label"),
            Label(self.my_username, id="user-name-label"),
            Label(" ●", id="online-label"),
            Label(" ", id="ping-label"),
            id="header-bar"
        )

        chat_container = ScrollableContainer(
            RichLog(id="chat-log", highlight=True, markup=True, wrap=True),
            id="chat-container"
        )

        sidebar = Vertical(
            Label("👥 Online", id="sidebar-title"),
            ListView(id="user-list"),
            id="sidebar"
        )

        main_area = Horizontal(
            chat_container,
            sidebar,
            id="main-area"
        )

        input_bar = Horizontal(
            Label(f"#{self.current_room}", id="room-indicator"),
            Input(placeholder="Ketik pesan atau /help...", id="msg-input"),
            Label("[↵ kirim]", id="send-hint"),
            id="input-bar"
        )

        status = Horizontal(
            Label("Terhubung • Ctrl+U sidebar • Ctrl+C keluar", id="status-text"),
            id="status-bar"
        )

        self.mount(header)
        self.mount(main_area)
        self.mount(input_bar)
        self.mount(status)

        self.update_header()
        self.update_status_bar()
        self.query_one("#msg-input").focus()
        self.append_divider()

    def update_header(self):
        try:
            if self.current_room == "global":
                room_disp = f"#{self.current_room}"
                online_disp = f" ● {self.online_count} online"
            else:
                room_disp = f"🔒 {self.current_room}"
                online_disp = " ● Private Room"

            self.query_one("#room-name-label", Label).update(room_disp)
            self.query_one("#online-label", Label).update(online_disp)
            self.query_one("#room-indicator", Label).update(room_disp)
        except NoMatches:
            pass

    def update_status_bar(self):
        try:
            if self.connected:
                if self.ping_ms >= 0:
                    if self.ping_ms < 100:
                        ping_color = "#34d399"
                    elif self.ping_ms < 250:
                        ping_color = "#fbbf24"
                    else:
                        ping_color = "#f87171"
                    ping_text = f"[{ping_color}]Ping: {self.ping_ms}ms[/{ping_color}]"
                else:
                    ping_text = "[#94a3b8]Ping: ...[/#94a3b8]"
                status = f"Terhubung • {ping_text} • Ctrl+U sidebar • Ctrl+C keluar"
            else:
                status = "[#f87171]● Terputus — Menghubungkan ulang...[/#f87171] • Ctrl+C keluar"

            self.query_one("#status-text", Label).update(status)

            if self.connected and self.ping_ms >= 0:
                if self.ping_ms < 100:
                    ping_color = "#34d399"
                elif self.ping_ms < 250:
                    ping_color = "#fbbf24"
                else:
                    ping_color = "#f87171"
                self.query_one("#ping-label", Label).update(f"[{ping_color}]{self.ping_ms}ms[/{ping_color}]")
            else:
                self.query_one("#ping-label", Label).update("")
        except NoMatches:
            pass

    def update_sidebar(self):
        try:
            user_list = self.query_one("#user-list", ListView)
            user_list.clear()
            for uname in self.online_users:
                marker = " (kamu)" if uname == self.my_username else ""
                item = ListItem(Label(f"  {uname}{marker}"))
                user_list.append(item)
        except NoMatches:
            pass

    def action_toggle_sidebar(self):
        try:
            sidebar = self.query_one("#sidebar")
            self.sidebar_visible = not self.sidebar_visible
            if self.sidebar_visible:
                sidebar.remove_class("hidden")
            else:
                sidebar.add_class("hidden")
        except NoMatches:
            pass

    def append_message(self, sender: str, text: str, time: str, is_me: bool):
        self.render_chat_message(sender, text, time, is_me)

    def append_system(self, text: str, time: str = ""):
        time_part = f"[{COLORS['time']}]{time}[/{COLORS['time']}] " if time else ""
        for line in text.split("\n"):
            self._write_msg(f"{time_part}[{COLORS['system']}]{line}[/{COLORS['system']}]")

    def append_divider(self):
        self._write_msg(f"[{COLORS['system']}]{'─' * 60}[/{COLORS['system']}]")

    def show_error(self, msg: str):
        try:
            self._write_msg(f"[{COLORS['error']}]✗ {msg}[/{COLORS['error']}]")
        except Exception:
            self.notify(msg, severity="error")

    def on_key(self, event: Key) -> None:
        try:
            input_widget = self.query_one("#msg-input", Input)
        except NoMatches:
            return

        if not input_widget.has_focus:
            return

        if event.key == "up":
            event.prevent_default()
            event.stop()
            if not self.sent_history:
                return
            if self.history_index == -1:
                self.history_temp = input_widget.value
                self.history_index = len(self.sent_history) - 1
            elif self.history_index > 0:
                self.history_index -= 1
            else:
                return
            input_widget.value = self.sent_history[self.history_index]
            input_widget.cursor_position = len(input_widget.value)

        elif event.key == "down":
            event.prevent_default()
            event.stop()
            if self.history_index == -1:
                return
            if self.history_index < len(self.sent_history) - 1:
                self.history_index += 1
                input_widget.value = self.sent_history[self.history_index]
            else:
                self.history_index = -1
                input_widget.value = self.history_temp
            input_widget.cursor_position = len(input_widget.value)

    def _add_to_history(self, text: str):
        if text and (not self.sent_history or self.sent_history[-1] != text):
            self.sent_history.append(text)
            if len(self.sent_history) > MAX_HISTORY:
                self.sent_history.pop(0)
        self.history_index = -1
        self.history_temp = ""

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text and event.input.id == "username-input":
            text = ""  # allow empty for random

        input_widget = event.input

        if input_widget.id == "username-input":
            if self.ws and not self.username_submitted:
                self.username_submitted = True
                await self.ws.send(json.dumps({
                    "type": "set_username",
                    "username": text
                }))
            elif not self.ws:
                self.notify("Menunggu koneksi ke server...", severity="warning")
            return

        if input_widget.id == "msg-input" and self.ws and self.connected:
            if not text:
                return

            self._add_to_history(text)

            if text.startswith("/"):
                parts = text.split(" ", 1)
                cmd = parts[0].lower()
                await process_user_command(self, cmd, parts, text)
            else:
                await process_chat_message(self, text)

            input_widget.value = ""

    def action_quit(self):
        for task in self._burn_tasks.values():
            task.cancel()
        self.exit()

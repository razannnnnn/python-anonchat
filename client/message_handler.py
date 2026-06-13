import json
from textual.widgets import RichLog
from textual.css.query import NoMatches
from .crypto import decrypt_msg

async def process_server_message(app, data: dict):
    msg_type = data.get("type")

    if msg_type == "welcome":
        app.my_username = data.get("username", "")
        app.current_room = data.get("room", "global")
        if not app.in_chat:
            app.switch_to_chat()
        elif not app.username_submitted:
            pass
        app.username_submitted = True
        app.append_system(data.get("text", ""))

    elif msg_type == "request_username":
        if app.username_submitted and app.my_username and app.ws:
            await app.ws.send(json.dumps({
                "type": "set_username",
                "username": app.my_username
            }))

    elif msg_type == "system":
        text = data.get("text", "")
        time_str = data.get("time", "")
        if not app.in_chat and text.startswith("Selamat datang, "):
            app.my_username = text[len("Selamat datang, "):].rstrip("!")
            app.current_room = "global"
            app.switch_to_chat()
        app.append_system(text, time_str)

    elif msg_type == "message":
        sender = data.get("from", "?")
        text = data.get("text", "")
        time_str = data.get("time", "")
        is_me = sender == app.my_username

        if app.current_room != "global":
            decrypted = decrypt_msg(text, app.room_password)
            app.render_chat_message(sender, decrypted, time_str, is_me)
        else:
            app.render_chat_message(sender, text, time_str, is_me)

    elif msg_type == "room_change":
        app.current_room = data.get("room", "global")
        if app.current_room == "global":
            app.room_password = ""
        app.update_header()
        try:
            app.query_one("#chat-log", RichLog).clear()
            app._msg_buffer.clear()
        except NoMatches:
            pass
        app.append_system(data.get("text", ""), data.get("time", ""))
        app.append_divider()

    elif msg_type == "online":
        app.online_count = data.get("count", 0)
        app.online_users = data.get("users", [])
        app.update_header()
        app.update_sidebar()

    elif msg_type == "history":
        messages = data.get("messages", [])
        if messages:
            for msg in messages:
                sender = msg.get("from", "?")
                text = msg.get("text", "")
                time_str = msg.get("time", "")
                is_me = sender == app.my_username
                app.render_chat_message(sender, text, time_str, is_me)

    elif msg_type == "whisper":
        sender = data.get("from", "?")
        text = data.get("text", "")
        time_str = data.get("time", "")
        app.last_whisper_from = sender
        app.append_whisper_in(sender, text, time_str)

    elif msg_type == "whisper_sent":
        target = data.get("to", "?")
        text = data.get("text", "")
        time_str = data.get("time", "")
        app.append_whisper_out(target, text, time_str)

    elif msg_type == "whisper_error":
        text = data.get("text", "")
        app.show_error(text)

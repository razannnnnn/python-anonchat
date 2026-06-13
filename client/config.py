# client/config.py

# Max messages to keep for self-destruct tracking
MAX_MSG_BUFFER = 500
# Max sent history entries
MAX_HISTORY = 50

COLORS = {
    "self":    "bold #38bdf8",
    "other":   "bold #f472b6",
    "system":  "italic #94a3b8",
    "error":   "bold #f87171",
    "info":    "bold #34d399",
    "time":    "#64748b",
    "room":    "bold #a78bfa",
    "whisper": "italic #c084fc",
    "mention": "bold #fbbf24",
    "burn":    "bold #f97316",
}

CSS = """
Screen {
    background: #0f172a;
}
#header-bar {
    height: 3;
    background: #1e293b;
    border-bottom: solid #334155;
    padding: 0 2;
    align: center middle;
}
#header-bar Label {
    margin: 0 1;
    text-style: bold;
    color: #e2e8f0;
}
#room-name-label {
    color: #38bdf8;
}
#user-name-label {
    color: #a78bfa;
}
#online-label {
    color: #34d399;
}
#ping-label {
    color: #34d399;
}
#main-area {
    height: 1fr;
}
#chat-container {
    border: round #334155;
    background: #0f172a;
    margin: 1 1 1 2;
    padding: 0 1;
    height: 1fr;
}
#chat-log {
    background: #0f172a;
    scrollbar-color: #38bdf8 #1e293b;
    scrollbar-color-hover: #7dd3fc #1e293b;
    scrollbar-color-active: #bae6fd #1e293b;
}
#sidebar {
    width: 24;
    background: #1e293b;
    border-left: solid #334155;
    margin: 1 2 1 0;
    padding: 1;
    display: block;
}
#sidebar.hidden {
    display: none;
}
#sidebar-title {
    text-style: bold;
    color: #38bdf8;
    margin-bottom: 1;
}
#user-list {
    background: #1e293b;
    height: 1fr;
    scrollbar-color: #475569 #1e293b;
    scrollbar-color-hover: #64748b #1e293b;
}
#user-list > ListItem {
    background: #1e293b;
    color: #e2e8f0;
    height: 1;
    padding: 0 1;
}
#user-list > ListItem.--highlight {
    background: #334155;
}
#input-bar {
    height: 3;
    background: #1e293b;
    border-top: solid #334155;
    padding: 0 2;
    align: left middle;
}
#room-indicator {
    color: #38bdf8;
    text-style: bold;
    margin-right: 1;
}
#msg-input {
    background: #0f172a;
    border: none;
    color: #f8fafc;
    width: 1fr;
}
#msg-input:focus {
    border: none;
}
#send-hint {
    color: #64748b;
    margin-left: 1;
}
#status-bar {
    height: 1;
    background: #0f172a;
    color: #475569;
    padding: 0 2;
}
#username-screen {
    align: center middle;
    background: #0f172a;
}
#username-box {
    width: 60;
    height: 15;
    background: #1e293b;
    border: round #38bdf8;
    padding: 2 4;
    align: center middle;
}
#username-title {
    text-style: bold;
    color: #38bdf8;
    margin-bottom: 1;
}
#username-subtitle {
    color: #94a3b8;
    margin-bottom: 2;
}
#username-input {
    background: #0f172a;
    border: solid #475569;
    color: #f8fafc;
}
#username-input:focus {
    border: solid #38bdf8;
}
"""

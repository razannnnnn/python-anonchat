import json
from textual.widgets import RichLog
from textual.css.query import NoMatches
from crypto import crypt_msg, encrypt_rsa

async def process_user_command(app, cmd: str, parts: list, text: str):
    if cmd == "/help":
        help_text = (
            "Panduan Perintah:\n"
            "  /help   - Menampilkan pesan bantuan ini\n"
            "  /clear  - Membersihkan layar obrolan\n"
            "  /quit   - Keluar dari aplikasi\n"
            "  /create <room> <pass> - Membuat private room dgn password\n"
            "  /join <room> <pass> - Masuk private room dgn password\n"
            "  /leave  - Keluar dari private room (kembali ke global)\n"
            "  /w <user> <pesan> - Kirim whisper/DM ke user\n"
            "  /r <pesan> - Balas whisper terakhir\n"
            "  /kick <user> - Keluarkan user dari room (owner only)\n"
            "  /ban <user> - Ban user dari room (owner only)\n"
            "  /unban <user> - Cabut ban user (owner only)\n"
            "  /burn <detik> <pesan> - Pesan yang otomatis hilang\n"
            "  /me <aksi> - Mengirim pesan aksi\n"
            "  /shrug  - Mengirim emoticon ¯\\_(ツ)_/¯\n"
            "  Ctrl+U  - Toggle sidebar online users\n"
            "  ↑ / ↓   - Navigasi riwayat pesan"
        )
        app.append_system(help_text)
    elif cmd == "/clear":
        try:
            app.query_one("#chat-log", RichLog).clear()
            app._msg_buffer.clear()
            app._msg_counter = 0
        except NoMatches:
            pass
    elif cmd == "/quit":
        app.action_quit()
    elif cmd == "/create":
        if len(parts) > 1:
            args = parts[1].split(" ", 1)
            if len(args) < 2:
                app.append_system("Penggunaan: /create <room> <password>")
            else:
                app.room_password = args[1]
                await app.ws.send(json.dumps({"type": "message", "text": f"/buatroom {args[0]} {args[1]}"}))
        else:
            app.append_system("Penggunaan: /create <room> <password>")
    elif cmd == "/join":
        if len(parts) > 1:
            args = parts[1].split(" ", 1)
            if len(args) < 2:
                app.append_system("Penggunaan: /join <room> <password>")
            else:
                app.room_password = args[1]
                await app.ws.send(json.dumps({"type": "message", "text": f"/join {args[0]} {args[1]}"}))
        else:
            app.append_system("Penggunaan: /join <room> <password>")
    elif cmd == "/leave":
        app.room_password = ""
        await app.ws.send(json.dumps({"type": "message", "text": "/global"}))
    elif cmd == "/w":
        if len(parts) > 1:
            w_parts = parts[1].split(" ", 1)
            if len(w_parts) < 2:
                app.append_system("Penggunaan: /w <username> <pesan>")
            else:
                target_name = w_parts[0]
                whisper_text = w_parts[1]
                
                # Store original text for local rendering
                original_text = whisper_text
                
                # Encrypt if we have their public key
                target_pub = app.public_keys.get(target_name)
                if target_pub:
                    whisper_text = encrypt_rsa(target_pub, whisper_text)
                else:
                    app.append_system(f"⚠ [Peringatan] Public Key untuk '{target_name}' tidak ditemukan di memori lokal. Pesan mungkin tidak terenkripsi RSA.")

                await app.ws.send(json.dumps({
                    "type": "whisper",
                    "to": target_name,
                    "text": whisper_text
                }))
                
                # Render locally
                import datetime
                app.append_whisper_out(target_name, original_text, datetime.datetime.now().strftime("%H:%M:%S"))
        else:
            app.append_system("Penggunaan: /w <username> <pesan>")
    elif cmd == "/r":
        if not app.last_whisper_from:
            app.append_system("Belum ada whisper yang bisa dibalas.")
        elif len(parts) > 1:
            whisper_text = parts[1]
            target_name = app.last_whisper_from
            
            # Store original text for local rendering
            original_text = whisper_text
            
            # Encrypt if we have their public key
            target_pub = app.public_keys.get(target_name)
            if target_pub:
                whisper_text = encrypt_rsa(target_pub, whisper_text)
            else:
                app.append_system(f"⚠ [Peringatan] Public Key untuk '{target_name}' tidak ditemukan di memori lokal. Pesan mungkin tidak terenkripsi RSA.")

            await app.ws.send(json.dumps({
                "type": "whisper",
                "to": target_name,
                "text": whisper_text
            }))
            
            # Render locally
            import datetime
            app.append_whisper_out(target_name, original_text, datetime.datetime.now().strftime("%H:%M:%S"))
        else:
            app.append_system("Penggunaan: /r <pesan>")
    elif cmd == "/burn":
        if len(parts) > 1:
            burn_parts = parts[1].split(" ", 1)
            if len(burn_parts) < 2:
                app.append_system("Penggunaan: /burn <detik> <pesan>")
            else:
                try:
                    burn_secs = int(burn_parts[0])
                    if burn_secs < 1 or burn_secs > 300:
                        app.append_system("Durasi burn harus 1-300 detik.")
                    else:
                        burn_text = burn_parts[1]
                        payload_text = f"[[BURN:{burn_secs}]] {burn_text}"
                        if app.current_room != "global":
                            payload_text = crypt_msg(payload_text, app.room_password)
                        await app.ws.send(json.dumps({"type": "message", "text": payload_text}))
                except ValueError:
                    app.append_system("Penggunaan: /burn <detik> <pesan> (detik harus angka)")
        else:
            app.append_system("Penggunaan: /burn <detik> <pesan>")
    elif cmd == "/shrug":
        payload_text = "¯\\_(ツ)_/¯"
        if app.current_room != "global":
            payload_text = crypt_msg(payload_text, app.room_password)
        await app.ws.send(json.dumps({"type": "message", "text": payload_text}))
    elif cmd == "/me":
        if len(parts) > 1:
            payload_text = f"*** {app.my_username} {parts[1]} ***"
            if app.current_room != "global":
                payload_text = crypt_msg(payload_text, app.room_password)
            await app.ws.send(json.dumps({"type": "message", "text": payload_text}))
        else:
            app.append_system("Penggunaan: /me <aksi>")
    elif cmd in ("/kick", "/ban", "/unban"):
        await app.ws.send(json.dumps({"type": "message", "text": text}))
    else:
        app.append_system(f"Perintah tidak dikenal: {cmd}. Ketik /help untuk panduan.")

async def process_chat_message(app, text: str):
    payload_text = text
    if app.current_room != "global":
        payload_text = crypt_msg(payload_text, app.room_password)
    await app.ws.send(json.dumps({"type": "message", "text": payload_text}))

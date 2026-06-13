import base64
import hashlib
from cryptography.fernet import Fernet

def get_fernet(password: str) -> Fernet:
    key = hashlib.sha256(password.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))

def crypt_msg(text: str, key: str) -> str:
    if not key: return text
    f = get_fernet(key)
    return f.encrypt(text.encode()).decode()

def decrypt_msg(encoded_text: str, key: str) -> str:
    if not key: return encoded_text
    f = get_fernet(key)
    try:
        return f.decrypt(encoded_text.encode()).decode()
    except Exception:
        return "🔒 [Pesan dienkripsi / Password salah]"

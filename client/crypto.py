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

# --- RSA Asymmetric Encryption ---
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend

def generate_rsa_keys():
    """Generates a new RSA public/private key pair."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key

def export_public_key(public_key) -> str:
    """Exports the public key to a PEM string."""
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem.decode('utf-8')

def import_public_key(pem_data: str):
    """Imports a public key from a PEM string."""
    return serialization.load_pem_public_key(
        pem_data.encode('utf-8'),
        backend=default_backend()
    )

def encrypt_rsa(public_key_pem: str, message: str) -> str:
    """Encrypts a string message using the target's public key PEM."""
    try:
        pub_key = import_public_key(public_key_pem)
        ciphertext = pub_key.encrypt(
            message.encode('utf-8'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return base64.b64encode(ciphertext).decode('utf-8')
    except Exception as e:
        return f"[ENCRYPTION ERROR: {e}]"

def decrypt_rsa(private_key, base64_ciphertext: str) -> str:
    """Decrypts a base64 ciphertext using the local private key."""
    try:
        ciphertext = base64.b64decode(base64_ciphertext)
        plaintext = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext.decode('utf-8')
    except Exception:
        return "🔒 [Gagal mendekripsi pesan (Kunci RSA tidak cocok)]"


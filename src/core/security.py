import os
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# La SECRET_KEY debe estar en el .env, si no, generamos una de fallback 
# (pero lo ideal es que sea persistente en el .env)
_SECRET = os.getenv("SECRET_KEY", "uE2z8X7K3dC_qR9pW5nV1mT4bS6aN8gL0kH2jG4fF_s=")

def encrypt_password(plain_text: str) -> str:
    if not plain_text:
        return ""
    f = Fernet(_SECRET.encode())
    return f.encrypt(plain_text.encode()).decode()

def decrypt_password(encrypted_text: str) -> str:
    if not encrypted_text:
        return ""
    try:
        f = Fernet(_SECRET.encode())
        return f.decrypt(encrypted_text.encode()).decode()
    except Exception:
        # Si falla la desencriptación (ej: cambió la clave or no estaba encriptada),
        # devolvemos el original como fallback de seguridad tras cambio
        return encrypted_text

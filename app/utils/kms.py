import base64
from functools import lru_cache
from google.cloud import kms_v1
from app.config import PROJECT_ID, LOCATION, KEYRING, KEY_NAME


@lru_cache
def get_kms_client():
    return kms_v1.KeyManagementServiceClient()


def _kms_key_path() -> str:
    required = [PROJECT_ID, LOCATION, KEYRING, KEY_NAME]
    if any(v is None for v in required):
        raise RuntimeError("Missing required KMS environment variables.")
    return get_kms_client().crypto_key_path(PROJECT_ID, LOCATION, KEYRING, KEY_NAME)


def encrypt_secret(plaintext: str) -> str:
    key_path = _kms_key_path()
    client = get_kms_client()
    encrypted = client.encrypt(
        request={"name": key_path, "plaintext": plaintext.encode("utf-8")}
    )
    return base64.b64encode(encrypted.ciphertext).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    key_path = _kms_key_path()
    client = get_kms_client()
    decrypted = client.decrypt(
        request={"name": key_path, "ciphertext": base64.b64decode(ciphertext)}
    )
    return decrypted.plaintext.decode("utf-8")

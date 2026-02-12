from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
import base64
import logging

logger = logging.getLogger(__name__)

class EncryptedCharField(models.CharField):
    """
    A CharField that encrypts its value using Fernet (symmetric encryption).
    Uses settings.SECRET_KEY to derive a key if ENCRYPTION_KEY is not set.
    """
    description = "Encrypted CharField"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fernet = self._get_fernet()

    def _get_fernet(self):
        try:
            # Try to get key from settings
            key = getattr(settings, 'ENCRYPTION_KEY', None)
            if not key:
                # Derive 32-byte key from SECRET_KEY
                secret = settings.SECRET_KEY
                # Pad or truncate to 32 bytes base64 encoded
                # Fernet requires a 32-byte url-safe base64-encoded key
                # Simple derivation for dev (in prod use proper key gen)
                import hashlib
                
                # Create a 32 byte key using SHA256 of the secret
                hasher = hashlib.sha256()
                hasher.update(secret.encode('utf-8'))
                digest = hasher.digest()
                
                # Base64 encode it to make it fernet compatible
                key = base64.urlsafe_b64encode(digest)
            
            return Fernet(key)
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            return None

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.decrypt(value)

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, str):
            # Try to decrypt to check if it's already encrypted (naive check)
            # Actually to_python is called after from_db_value, so if it was decrypted there, it's fine.
            # But it's also called on assignment.
            # We assume the value passed to to_python is DECRYPTED (plain text) unless it came from DB
            # But Django calls to_python on value assignment in models too? 
            # No, mostly from forms or deserialization.
            return value
        return value

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return value
        return self.encrypt(str(value))

    def encrypt(self, value):
        if not self._fernet:
            return value
        try:
            # encrypt requires bytes
            encrypted = self._fernet.encrypt(value.encode('utf-8'))
            # database expects string
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return value

    def decrypt(self, value):
        if not self._fernet:
            return value
        try:
            # value from db is string, decrypt requires bytes
            decrypted = self._fernet.decrypt(value.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception as e:
            # If decryption fails (e.g. old plain data or wrong key), return raw
            # This is safer for migration from plain to encrypted
            # logger.warning(f"Decryption failed, returning raw value: {e}")
            return value

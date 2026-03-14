from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
import base64
import hashlib
import logging

logger = logging.getLogger(__name__)


class EncryptedCharField(models.CharField):
    """
    حقل نصي مشفر باستخدام Fernet (تشفير متماثل).
    يستخدم settings.ENCRYPTION_KEY أو يستمد مفتاحاً من settings.SECRET_KEY.
    """
    description = "حقل نصي مشفر"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fernet = self._get_fernet()

    def _get_fernet(self):
        """الحصول على مفتاح التشفير وإنشاء كائن Fernet"""
        try:
            # محاولة الحصول على المفتاح من الإعدادات
            key = getattr(settings, 'ENCRYPTION_KEY', None)
            
            if not key:
                # استنتاج مفتاح 32 بايت من SECRET_KEY
                secret = settings.SECRET_KEY
                
                # إنشاء مفتاح 32 بايت باستخدام SHA256
                hasher = hashlib.sha256()
                hasher.update(secret.encode('utf-8'))
                digest = hasher.digest()
                
                # ترميز Base64 ليكون متوافقاً مع Fernet
                key = base64.urlsafe_b64encode(digest)
            
            return Fernet(key)
            
        except Exception as e:
            logger.error(f"فشل في تهيئة التشفير: {e}")
            return None

    def from_db_value(self, value, expression, connection):
        """تحويل القيمة من قاعدة البيانات"""
        if value is None:
            return value
        return self._decrypt(value)

    def to_python(self, value):
        """تحويل القيمة إلى كائن Python"""
        if value is None:
            return value
        return value

    def get_prep_value(self, value):
        """تحضير القيمة لحفظها في قاعدة البيانات"""
        value = super().get_prep_value(value)
        if value is None:
            return value
        return self._encrypt(str(value))

    def _encrypt(self, value):
        """تشفير القيمة"""
        if not self._fernet:
            logger.warning("التشفير غير متاح، يتم حفظ القيمة كنص عادي")
            return value
        
        try:
            encrypted = self._fernet.encrypt(value.encode('utf-8'))
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"فشل التشفير: {e}")
            return value

    def _decrypt(self, value):
        """فك تشفير القيمة"""
        if not self._fernet:
            return value
        
        try:
            decrypted = self._fernet.decrypt(value.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception as e:
            # إذا فشل فك التشفير (بيانات قديمة أو مفتاح خاطئ)
            logger.warning(f"فشل فك التشفير، إرجاع القيمة الأصلية: {e}")
            return value
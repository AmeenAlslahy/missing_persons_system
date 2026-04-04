from rest_framework import serializers

class ErrorResponseSerializer(serializers.Serializer):
    """سرياليزر لتوثيق هيكل الأخطاء الموحد في النظام"""
    success = serializers.BooleanField(default=False)
    error_code = serializers.CharField()
    message = serializers.CharField()  # بالعربية
    message_en = serializers.CharField(required=False)  # بالإنجليزية
    details = serializers.DictField(required=False)
    timestamp = serializers.DateTimeField()

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import logging

logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncWebsocketConsumer):
    """مستهلك WebSocket للإشعارات الفورية"""
    
    async def connect(self):
        self.user = self.scope["user"]
        
        if self.user.is_authenticated:
            self.group_name = f"user_{self.user.id}_notifications"
            
            # الانضمام لمجموعة المستخدم الخاصة
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            await self.accept()
            logger.info(f"اتصال WebSocket ناجح للمستخدم {self.user.id}")
        else:
            await self.close()
            logger.warning("محاولة اتصال WebSocket من مستخدم غير مصرح له")

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            logger.info(f"قطع اتصال WebSocket للمستخدم {self.user.id}")

    async def receive(self, text_data):
        """استقبال رسائل من العميل (مثل تحديد كـ مقروء)"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'mark_as_read':
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_as_read(notification_id)
                    
        except Exception as e:
            logger.error(f"خطأ في معالجة رسالة WebSocket: {e}")

    async def send_notification(self, event):
        """إرسال إشعار للعميل"""
        notification = event['notification']
        
        # إرسال الرسالة عبر WebSocket
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': notification
        }))

    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        """تحديد الإشعار كمقروء في قاعدة البيانات"""
        from .models import Notification
        try:
            notification = Notification.objects.get(
                notification_id=notification_id, 
                user=self.user
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False

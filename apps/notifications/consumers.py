"""WebSocket consumer — `/ws/` umumiy endpoint.

Frontend `useAppWebSocket` shu URL'ga ulanadi va kanallar bo'yicha xabar oladi:
- `notify` — bildirishnoma
- `chat` — xabar (chat app yaratilganda)
- `report` — task/request (reports app yaratilganda)
"""
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class UnifiedConsumer(AsyncJsonWebsocketConsumer):
    """Bitta global socket — barcha kanallar uchun."""

    async def connect(self):
        user = self.scope.get('user')
        if not user or not getattr(user, 'is_authenticated', False):
            await self.close(code=4401)
            return

        self.user = user
        self.user_id = str(user.id)

        # Foydalanuvchi guruhlariga qo'shilish (notification, chat, report — kelajakda)
        for group in self._user_groups():
            await self.channel_layer.group_add(group, self.channel_name)

        await self.accept()

    def _user_groups(self):
        return [
            f'notify_{self.user_id}',
            f'chat_{self.user_id}',
            f'report_{self.user_id}',
        ]

    async def disconnect(self, code):
        if not getattr(self, 'user_id', None):
            return
        for group in self._user_groups():
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        """Client → server xabar.

        Qo'llab-quvvatlanadigan kanallar:
        - `ping` — keep-alive
        - `chat` — yangi xabar yuborish (production `/app/talking` ekvivalenti)
        - `notify.read` — bildirishnoma ko'rilgan deb belgilash
        """
        channel = content.get('channel')
        if channel == 'ping':
            await self.send_json({'channel': 'pong'})
            return

        if channel == 'chat':
            from channels.db import database_sync_to_async

            from apps.chat.services import ChatService

            receiver_id = content.get('to')
            message = (content.get('message') or '').strip()
            if not receiver_id or not message:
                return

            try:
                msg = await database_sync_to_async(ChatService.send)(
                    sender=self.user, receiver_id=receiver_id, message=message,
                )
                # Sender'ga ham echo (UI darhol ko'rsatish uchun)
                await self.send_json({
                    'channel': 'chat',
                    'from': self.user_id,
                    'to': str(receiver_id),
                    'message_id': str(msg.id),
                    'message': msg.message,
                    'created_at': msg.created_at.isoformat(),
                    'echo': True,
                })
            except Exception as e:  # noqa: BLE001
                logger.warning(f'WS chat send xatosi: {e}')

    # group_send'dan kelgan xabarlarni client'ga forward qilish
    async def notify_message(self, event):
        await self.send_json(event['payload'])

    async def chat_message(self, event):
        await self.send_json(event['payload'])

    async def report_message(self, event):
        await self.send_json(event['payload'])

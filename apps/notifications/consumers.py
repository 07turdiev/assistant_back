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

        Hozircha asosan ping-pong va kelajakda chat send.
        """
        channel = content.get('channel')
        if channel == 'ping':
            await self.send_json({'channel': 'pong'})
            return
        # boshqalari (chat send va h.k.) keyingi sprintda

    # group_send'dan kelgan xabarlarni client'ga forward qilish
    async def notify_message(self, event):
        await self.send_json(event['payload'])

    async def chat_message(self, event):
        await self.send_json(event['payload'])

    async def report_message(self, event):
        await self.send_json(event['payload'])

"""VAPID kalit juftligini generatsiya qilish.

Bir martalik komanda. Natijani `.env` ga (yoki settings'ga) qo'lda ko'chirish kerak:

    VAPID_PUBLIC_KEY=...
    VAPID_PRIVATE_KEY=...

Keyinchalik `.env`'da bu qiymatlar saqlanadi.
"""
import base64

from django.core.management.base import BaseCommand
from py_vapid import Vapid


class Command(BaseCommand):
    help = 'VAPID kalit juftligini yaratadi (Web Push uchun)'

    def handle(self, *args, **options):
        vapid = Vapid()
        vapid.generate_keys()

        # Public key — uncompressed format (65 bytes), base64url
        raw_public = vapid.public_key.public_numbers().x.to_bytes(32, 'big') + \
                     vapid.public_key.public_numbers().y.to_bytes(32, 'big')
        public_b64 = base64.urlsafe_b64encode(b'\x04' + raw_public).rstrip(b'=').decode('ascii')

        # Private key — D parameter (32 bytes), base64url
        raw_private = vapid.private_key.private_numbers().private_value.to_bytes(32, 'big')
        private_b64 = base64.urlsafe_b64encode(raw_private).rstrip(b'=').decode('ascii')

        self.stdout.write(self.style.SUCCESS('VAPID kalitlari yaratildi'))
        self.stdout.write('')
        self.stdout.write('Quyidagilarni `.env` ga qo\'shing:')
        self.stdout.write('')
        self.stdout.write(f'VAPID_PUBLIC_KEY={public_b64}')
        self.stdout.write(f'VAPID_PRIVATE_KEY={private_b64}')
        self.stdout.write('VAPID_CLAIMS_EMAIL=mailto:admin@madaniyat.uz')

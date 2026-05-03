"""Telegram bot launcher.

Usage:
    python manage.py run_bot

Production'da systemd service sifatida ishga tushiriladi:
    /etc/systemd/system/assistant-bot.service
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Telegram bot polling ishga tushiradi (alohida process)'

    def handle(self, *args, **options):
        from apps.telegram_bot.bot import main
        main()

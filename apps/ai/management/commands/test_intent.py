"""Intent parser uchun batch test runner.

Foydalanish:
    python manage.py test_intent              # barcha test holatlarni
    python manage.py test_intent --case 5     # faqat 5-holat
    python manage.py test_intent --verbose    # to'liq diff bilan
    python manage.py test_intent --text "Ertaga 14 da kollegiya"  # bitta matnni sinab ko'rish

Test natijalari accuracy hisoblab beradi va xatoliklarni ko'rsatadi.
"""
from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.ai.services import parse_intent
from apps.ai.services.llm import OllamaClient, OllamaError


TEST_FILE = Path(__file__).resolve().parent.parent.parent / 'test_cases.json'


class Command(BaseCommand):
    help = 'Intent parser modelini o\'zbekcha test holatlar bilan sinab ko\'radi'

    def add_arguments(self, parser):
        parser.add_argument(
            '--case', type=int, default=None,
            help='Faqat shu ID test holatini ishga tushirish',
        )
        parser.add_argument(
            '--verbose', action='store_true',
            help='Har bir test uchun to\'liq JSON natijani ko\'rsatish',
        )
        parser.add_argument(
            '--text', type=str, default=None,
            help='Test holatlardan tashqari, oddiy matnni sinab ko\'rish',
        )

    def handle(self, *args, **options):
        # Sog'liq tekshiruvi
        client = OllamaClient()
        if not client.health():
            raise CommandError(
                f'Ollama server ishlamayapti: {client.base_url}\n'
                f'Ishga tushirish: ollama serve'
            )
        self.stdout.write(self.style.SUCCESS(f'[OK] Ollama server: {client.base_url}, model: {client.model}'))
        self.stdout.write('')

        # Bitta matnni sinab ko'rish rejimi
        if options['text']:
            self._run_single_text(options['text'])
            return

        # Test fayldan o'qish
        if not TEST_FILE.exists():
            raise CommandError(f'Test fayl topilmadi: {TEST_FILE}')

        with TEST_FILE.open('r', encoding='utf-8') as f:
            test_data = json.load(f)

        today_str = test_data.get('today', date.today().isoformat())
        today = date.fromisoformat(today_str)
        cases = test_data['cases']

        if options['case']:
            cases = [c for c in cases if c['id'] == options['case']]
            if not cases:
                raise CommandError(f'ID={options["case"]} test holat topilmadi')

        self.stdout.write(f'Test sanasi: {today_str}')
        self.stdout.write(f'Test holatlar: {len(cases)} ta\n')

        passed = 0
        failed_ids = []
        total_time = 0.0

        for case in cases:
            ok, elapsed = self._run_case(case, today=today, verbose=options['verbose'])
            total_time += elapsed
            if ok:
                passed += 1
            else:
                failed_ids.append(case['id'])

        self.stdout.write('')
        self.stdout.write('=' * 60)
        accuracy = passed / len(cases) * 100 if cases else 0
        self.stdout.write(f'Natija: {passed}/{len(cases)} ({accuracy:.1f}% accuracy)')
        self.stdout.write(f'O\'rtacha vaqt: {total_time / len(cases):.2f}s/test')
        if failed_ids:
            self.stdout.write(self.style.WARNING(f'Xatolik: holatlar #{failed_ids}'))
        self.stdout.write('=' * 60)

    def _run_single_text(self, text: str):
        self.stdout.write(self.style.HTTP_INFO(f'Matn: {text}'))
        start = time.monotonic()
        try:
            result, warnings = parse_intent(text)
        except OllamaError as e:
            self.stdout.write(self.style.ERROR(f'XATO: {e}'))
            return
        elapsed = time.monotonic() - start
        self.stdout.write(f'Vaqt: {elapsed:.2f}s')
        if warnings:
            for w in warnings:
                self.stdout.write(self.style.WARNING(f'OGOH: {w}'))
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))

    def _run_case(self, case: dict, *, today: date, verbose: bool) -> tuple[bool, float]:
        case_id = case['id']
        category = case.get('category', '')
        text = case['input']
        expected = case['expected']

        start = time.monotonic()
        try:
            actual, _warnings = parse_intent(text, today=today)
        except (OllamaError, ValueError) as e:
            elapsed = time.monotonic() - start
            self.stdout.write(self.style.ERROR(f'#{case_id} [{category}] CRASH: {e}'))
            return False, elapsed
        elapsed = time.monotonic() - start

        mismatches = self._compare(expected, actual)
        if not mismatches:
            self.stdout.write(self.style.SUCCESS(f'#{case_id} [{category}] OK ({elapsed:.2f}s)'))
            if verbose:
                self.stdout.write(f'    {json.dumps(actual, ensure_ascii=False)}')
            return True, elapsed

        self.stdout.write(self.style.ERROR(f'#{case_id} [{category}] FAIL ({elapsed:.2f}s)'))
        self.stdout.write(f'    Matn:    {text}')
        for field, exp_val, act_val in mismatches:
            self.stdout.write(f'    {field}: kutilgan={exp_val!r}, olingan={act_val!r}')
        if verbose:
            self.stdout.write(f'    To\'liq: {json.dumps(actual, ensure_ascii=False)}')
        return False, elapsed

    @staticmethod
    def _compare(expected: dict[str, Any], actual: dict[str, Any]) -> list[tuple[str, Any, Any]]:
        """Faqat `expected` ichidagi maydonlarni solishtiradi."""
        mismatches = []
        for field, exp_val in expected.items():
            act_val = actual.get(field)
            if isinstance(exp_val, list) and isinstance(act_val, list):
                # Tartibsiz solishtirish (case-insensitive list elementlari uchun)
                exp_norm = sorted(str(x).lower() for x in exp_val)
                act_norm = sorted(str(x).lower() for x in act_val)
                if exp_norm != act_norm:
                    mismatches.append((field, exp_val, act_val))
            elif exp_val != act_val:
                mismatches.append((field, exp_val, act_val))
        return mismatches

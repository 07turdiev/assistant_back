"""UzbekVoice.ai STT (Speech-to-Text) klienti.

API hujjat: https://uzbekvoice.ai/api/v1/stt
- Maks audio: 50MB / 60 daqiqa
- 1 daqiqadan uzun bo'lsa, blocking=false majburiy
- Qo'llab-quvvatlanuvchi tillar: 'uz', 'ru', 'uz-ru'
- Modellar: 'general' (umumiy), 'enhanced-stt' (faqat o'zbek uchun optimallashtirilgan)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import BinaryIO

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class STTError(RuntimeError):
    """STT API bilan bog'liq xatolik."""


class UzbekVoiceClient:
    """UzbekVoice.ai STT klienti.

    Misol:
        client = UzbekVoiceClient()
        text = client.transcribe(open('voice.ogg', 'rb'))
    """

    BASE_URL = 'https://uzbekvoice.ai/api/v1/stt'
    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
    BLOCKING_MAX_SECONDS = 60  # 1 daqiqa

    def __init__(self, api_key: str | None = None, timeout: float = 120.0):
        self.api_key = api_key or getattr(settings, 'UZBEKVOICE_API_KEY', '')
        if not self.api_key:
            raise STTError('UZBEKVOICE_API_KEY .env da sozlanmagan')
        self.timeout = timeout

    def transcribe(
        self,
        file: BinaryIO | Path | str,
        *,
        language: str = 'uz',
        model: str = 'general',
        run_diarization: str = 'false',
        return_offsets: bool = False,
        blocking: bool = True,
    ) -> str:
        """Audio faylni matnga aylantiradi.

        Args:
            file: ochiq fayl obyekti yoki yo'l (str/Path)
            language: 'uz' | 'ru' | 'uz-ru'
            model: 'general' | 'enhanced-stt'
            run_diarization: 'true' | 'false' | 'phone' (so'zlovchilarni bo'lish)
            return_offsets: vaqt belgilarini qaytarish
            blocking: True bo'lsa, transkript tugaguniga qadar kutadi

        Returns:
            Transkripsiya matni (str).
        """
        # Fayl obyekti tayyorlash
        close_after = False
        if isinstance(file, (str, Path)):
            file_path = Path(file)
            if not file_path.exists():
                raise STTError(f'Fayl topilmadi: {file_path}')
            if file_path.stat().st_size > self.MAX_FILE_SIZE_BYTES:
                raise STTError(f'Fayl juda katta (>{self.MAX_FILE_SIZE_BYTES} byte)')
            file_obj = open(file_path, 'rb')
            file_name = file_path.name
            close_after = True
        else:
            file_obj = file
            file_name = getattr(file, 'name', 'audio.ogg')

        try:
            files = {'file': (file_name, file_obj)}
            data = {
                'return_offsets': str(return_offsets).lower(),
                'run_diarization': run_diarization,
                'language': language,
                'model': model,
                'blocking': str(blocking).lower(),
            }
            headers = {'Authorization': self.api_key}

            try:
                response = requests.post(
                    self.BASE_URL,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=self.timeout,
                )
            except requests.exceptions.Timeout:
                raise STTError('STT API javob vaqti tugadi')
            except requests.exceptions.RequestException as e:
                raise STTError(f'STT API ga ulanmadi: {e}') from e

            if response.status_code != 200:
                logger.error('STT API xato: %s — %s', response.status_code, response.text[:300])
                raise STTError(f'STT API status {response.status_code}: {response.text[:200]}')

            body = response.json()
            return self._extract_text(body)

        finally:
            if close_after:
                file_obj.close()

    @staticmethod
    def _extract_text(body: dict) -> str:
        """Javobdan matnni ajratib oladi.

        UzbekVoice javob formati varianti turli bo'lishi mumkin — barcha mumkin maydonlarni tekshiramiz.
        """
        # Eng keng tarqalgan kalitlar
        for key in ('text', 'transcript', 'transcription', 'result'):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        # `result.text` ko'rinishi
        result = body.get('result')
        if isinstance(result, dict):
            for key in ('text', 'transcript'):
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        # `data.text`
        data = body.get('data')
        if isinstance(data, dict):
            for key in ('text', 'transcript'):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        logger.warning('STT javobida matn topilmadi: %s', body)
        raise STTError(f'STT javobida matn topilmadi. Javob kalitlari: {list(body.keys())}')

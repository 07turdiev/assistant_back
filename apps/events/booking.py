"""Yig'ilish zalsi bandligi — to'qnashuv aniqlash va tadbir bilan sinxronlash.

Yagona model `HallBooking` ikki manbadan to'ladi:
  - tadbir vazirlik zalsida bo'lsa (`event` bog'langan),
  - bo'lim alohida band qilsa (`event` bo'sh).

To'qnashuv: bir zal, bir kun, vaqt oralig'i ustma-ust bo'lsa — qattiq bloklanadi.
"""
from __future__ import annotations

from rest_framework.exceptions import ValidationError

from .models import HallBooking


def find_conflict(*, hall_id, date, start_time, end_time, exclude_booking_id=None):
    """Berilgan zal/vaqt uchun mavjud band bronni qaytaradi (yo'q bo'lsa None).

    Vaqt ustma-ustligi: start < other.end AND end > other.start.
    """
    if not hall_id or not date or not start_time or not end_time:
        return None
    qs = HallBooking.objects.filter(hall_id=hall_id, date=date)
    if exclude_booking_id:
        qs = qs.exclude(pk=exclude_booking_id)
    qs = qs.filter(start_time__lt=end_time, end_time__gt=start_time)
    return qs.select_related('event', 'direction', 'hall').first()


def conflict_message(booking) -> str:
    """To'qnashuv haqidagi tushunarli xabar (kim band qilgan)."""
    when = f"{booking.start_time.strftime('%H:%M')}–{booking.end_time.strftime('%H:%M')}"
    if booking.event_id and booking.event:
        by = f"«{booking.event.title}» tadbiri"
    elif booking.direction_id and booking.direction:
        by = f"{booking.direction.name_uz} bo'limi"
    elif booking.title:
        by = booking.title
    else:
        by = 'band qilingan'
    return f"Bu zal {when} oralig'ida allaqachon band ({by}). Boshqa vaqt yoki zal tanlang."


def assert_no_conflict(*, hall_id, date, start_time, end_time, exclude_booking_id=None) -> None:
    """To'qnashuv bo'lsa ValidationError ko'taradi (qattiq bloklash)."""
    conflict = find_conflict(
        hall_id=hall_id, date=date, start_time=start_time, end_time=end_time,
        exclude_booking_id=exclude_booking_id,
    )
    if conflict:
        raise ValidationError({'hall': conflict_message(conflict)})


def sync_event_booking(event) -> None:
    """Tadbirning zalsiga qarab bronni yaratadi/yangilaydi/o'chiradi.

    - zal tanlangan bo'lsa → bron (event bog'langan) yaratiladi/yangilanadi,
    - zal bo'sh bo'lsa → mavjud bron o'chiriladi (tashqi hududga o'tgan).
    """
    existing = HallBooking.objects.filter(event=event).first()

    if not event.hall_id:
        if existing:
            existing.delete()
        return

    if existing:
        existing.hall_id = event.hall_id
        existing.date = event.date
        existing.start_time = event.start_time
        existing.end_time = event.end_time
        existing.direction_id = event.direction_id
        existing.title = event.title
        existing.save(update_fields=[
            'hall', 'date', 'start_time', 'end_time', 'direction', 'title', 'updated_at',
        ])
    else:
        HallBooking.objects.create(
            hall_id=event.hall_id,
            date=event.date,
            start_time=event.start_time,
            end_time=event.end_time,
            direction_id=event.direction_id,
            event=event,
            title=event.title,
        )

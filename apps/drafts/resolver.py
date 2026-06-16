"""AI intent → DB obyektlari resolver.

Vazifalar:
1. AI chiqargan ism-familiyalarni `User` jadvalida topish
2. AI chiqargan bo'lim nomini `Direction` jadvalida topish
3. Asosiy oluvchi (`assigned_to`) ni aniqlash:
   - Agar bo'lim aytilsa → o'sha bo'lim HEAD'i
   - Aks holda → sender'ning bo'ysunuvchisi (chief=sender)

Mantiq Qaror 2'dan:
"Yaratuvchi hodimning ovozli xabari aytilgan hodimlarga BORMAYDI.
O'zidan quyi turuvchi hodimga boradi. Aytilgan qatnashuvchilar — qatnashuvchilarga qo'shiladi.
Bo'lim aytilsa — o'sha bo'limning boshlig'iga boradi."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.db.models import Q

if TYPE_CHECKING:
    from apps.directions.models import Direction
    from apps.users.models import User


@dataclass
class ResolveResult:
    """Resolver natijasi."""
    assigned_to: 'User | None' = None
    target_direction: 'Direction | None' = None
    parent_direction: 'Direction | None' = None
    suggested_participants: list = field(default_factory=list)
    unresolved_names: list[str] = field(default_factory=list)
    # Bot foydalanuvchidan tanlashni so'rashi kerak bo'lgan holatlar
    needs_user_choice: bool = False
    candidate_subordinates: list = field(default_factory=list)
    # Ogohlantirishlar (UI'da ko'rsatish uchun)
    warnings: list[str] = field(default_factory=list)


def resolve_intent(
    *,
    intent: dict,
    sender: 'User',
    raw_text: str = '',
) -> ResolveResult:
    """AI intent'ni DB obyektlariga moslashtiradi.

    Args:
        intent: parse_intent() natijasi
        sender: ovozli xabarni yuborgan User
        raw_text: STT chiqargan asl matn ("barcha rahbarlar" kabi iboralarni aniqlash uchun)

    Returns:
        ResolveResult — assigned_to, target_direction, suggested_participants va h.k.
    """
    result = ResolveResult()

    # 0. Yuqori turuvchi bo'lim (parent) aytilganmi?
    parent_dept_name = (intent.get('parent_department') or '').strip()
    if parent_dept_name:
        p_direction = _resolve_direction(parent_dept_name)
        if p_direction:
            result.parent_direction = p_direction
        else:
            result.warnings.append(f'"{parent_dept_name}" — bunday yuqori turuvchi bo\'lim topilmadi')

    # 1. Bo'lim aytilganmi?
    target_dept_name = (intent.get('target_department') or '').strip()
    if target_dept_name:
        direction = _resolve_direction(target_dept_name)
        if direction:
            result.target_direction = direction
            head = _find_head_of_direction(direction)
            if head:
                result.assigned_to = head
            else:
                result.warnings.append(
                    f'"{direction.name_uz}" bo\'limi topildi, ammo HEAD foydalanuvchi mavjud emas'
                )
        else:
            result.warnings.append(f'"{target_dept_name}" — bunday bo\'lim DB\'da topilmadi')

    # 2. Aytilgan ismlarni User'ga moslash (suggested_participants uchun)
    mentioned_names = intent.get('mentioned_participants') or []
    matched, unmatched = _resolve_user_names(mentioned_names)
    result.suggested_participants = matched
    result.unresolved_names = unmatched

    # 2.5 "barcha bo'lim rahbarlari" / "hamma boshliqlar" — barcha HEAD'larni avtomatik qo'shamiz
    scan_text = ' '.join(filter(None, [
        raw_text,
        intent.get('description') or '',
        ' '.join(mentioned_names),
    ]))
    all_heads_requested = _wants_all_heads(scan_text)
    if all_heads_requested:
        existing_ids = {u.id for u in result.suggested_participants}
        heads = [h for h in _get_all_heads() if h.id not in existing_ids]
        result.suggested_participants.extend(heads)
        # "barcha rahbarlar" deyilgan bo'lsa, AI topa olmagan ismlar shovqindir — tozalaymiz
        result.unresolved_names = []
        if heads:
            result.warnings.append(f"Barcha bo'lim rahbarlari qo'shildi ({len(heads)} ta)")
        else:
            result.warnings.append("Bo'lim rahbarlari (HEAD) DB'da topilmadi")

    # 3. Agar bo'lim aytilmasdan, oluvchi sender'ning bo'ysunuvchilaridan tanlanadi
    if not result.assigned_to and not target_dept_name:
        subordinates = list(_get_subordinates(sender))
        if len(subordinates) == 1:
            result.assigned_to = subordinates[0]
        elif len(subordinates) > 1:
            # Ko'p bo'ysunuvchi — bot foydalanuvchidan tanlashni so'raydi
            result.needs_user_choice = True
            result.candidate_subordinates = subordinates
            # Default — birinchisini tayinlaymiz (foydalanuvchi keyin o'zgartirsa bo'ladi)
            result.assigned_to = subordinates[0]
        elif all_heads_requested:
            # "Barcha rahbarlar" aytilgan, bo'ysunuvchi yo'q — yuboruvchi o'zi ko'rib joylashtiradi
            result.assigned_to = sender
        else:
            result.warnings.append(
                'Sizda bo\'ysunuvchi xodim yo\'q — qoralama uchun oluvchini saytda qo\'lda tanlang'
            )

    return result


# ---------- DIRECTION FUZZY MATCH ----------

def _resolve_direction(name: str) -> 'Direction | None':
    """Bo'lim nomini Direction'ga moslaydi.

    Strategiya:
    1. Aniq mos kelishi (`iexact`)
    2. Substring (`icontains`) — uzun nomlar uchun
    3. Birinchi necha so'z bo'yicha (so'z chegarasini hurmat qilish)
    """
    from apps.directions.models import Direction

    name_clean = name.strip()
    if not name_clean:
        return None

    # 1. Aniq moslashish (uz yoki ru)
    direction = Direction.objects.filter(
        Q(name_uz__iexact=name_clean) | Q(name_ru__iexact=name_clean)
    ).first()
    if direction:
        return direction

    # 2. Substring (foydalanuvchi to'liq aytmagan bo'lishi mumkin)
    direction = Direction.objects.filter(
        Q(name_uz__icontains=name_clean) | Q(name_ru__icontains=name_clean)
    ).first()
    if direction:
        return direction

    # 3. Birinchi 2 so'z bo'yicha
    words = name_clean.split()
    if len(words) >= 2:
        first_two = ' '.join(words[:2])
        direction = Direction.objects.filter(
            Q(name_uz__icontains=first_two) | Q(name_ru__icontains=first_two)
        ).first()
        if direction:
            return direction

    # 4. Birinchi so'z bo'yicha (oxirgi imkoniyat)
    direction = Direction.objects.filter(
        Q(name_uz__icontains=words[0]) | Q(name_ru__icontains=words[0])
    ).first()
    return direction


def _find_head_of_direction(direction: 'Direction') -> 'User | None':
    """Bo'limning HEAD rolidagi xodimini topadi."""
    from apps.users.enums import RoleName
    from apps.users.models import User
    return User.objects.filter(
        direction=direction,
        role__name=RoleName.HEAD,
        enabled=True,
    ).first()


# ---------- "BARCHA RAHBARLAR" ANIQLASH ----------

# "barcha", "hamma" + "rahbar"/"boshliq"/"rais" iboralarini aniqlash uchun kalit so'zlar
_ALL_WORDS = ('barcha', 'hamma', 'barchasi', 'butun', 'jami')
_HEAD_WORDS = ('rahbar', 'boshli', 'rais')  # boshli -> boshliq, boshliqlar, boshlig'i


def _wants_all_heads(text: str) -> bool:
    """Matnda "barcha bo'lim rahbarlari" / "hamma boshliqlar" kabi ibora bormi?

    "barcha"/"hamma" + "rahbar"/"boshliq"/"rais" birga uchrasa True qaytaradi.
    """
    if not text:
        return False
    t = text.lower()
    return any(w in t for w in _ALL_WORDS) and any(w in t for w in _HEAD_WORDS)


def _get_all_heads() -> list:
    """Barcha faol HEAD (bo'lim boshlig'i) foydalanuvchilarini qaytaradi."""
    from apps.users.enums import RoleName
    from apps.users.models import User
    return list(
        User.objects.filter(role__name=RoleName.HEAD, enabled=True).order_by('last_name', 'first_name')
    )


# ---------- USER NAME FUZZY MATCH ----------

def _resolve_user_names(names: list[str]) -> tuple[list, list[str]]:
    """Ismlar ro'yxatini User obyektlariga moslaydi.

    Returns:
        (matched_users, unmatched_names) — moslangan User'lar va moslanmagan ismlar
    """
    from apps.users.models import User

    matched: list = []
    unmatched: list[str] = []
    seen_user_ids = set()

    for name in names:
        name_clean = name.strip()
        if not name_clean:
            continue

        # Bir nechta so'z — ehtimol "Ism Familiya" yoki "Familiya Ism"
        words = name_clean.split()

        candidates = User.objects.filter(enabled=True)

        if len(words) == 1:
            # Faqat bitta so'z — ism yoki familiya bo'lishi mumkin
            candidates = candidates.filter(
                Q(first_name__iexact=words[0])
                | Q(last_name__iexact=words[0])
                | Q(father_name__iexact=words[0])
            )
        else:
            # Bir nechta so'z — har biri ism/familiya/ota ismi bo'lishi mumkin
            queries = Q()
            for word in words:
                queries &= (
                    Q(first_name__iexact=word)
                    | Q(last_name__iexact=word)
                    | Q(father_name__iexact=word)
                )
            candidates = candidates.filter(queries)

        user = candidates.first()
        if user and user.id not in seen_user_ids:
            matched.append(user)
            seen_user_ids.add(user.id)
        elif not user:
            # Aniq mos topilmadi — substring sinab ko'ramiz
            user = User.objects.filter(
                enabled=True,
            ).filter(
                Q(first_name__icontains=words[0]) | Q(last_name__icontains=words[0])
            ).first()
            if user and user.id not in seen_user_ids:
                matched.append(user)
                seen_user_ids.add(user.id)
            else:
                unmatched.append(name_clean)

    return matched, unmatched


# ---------- SUBORDINATE LOOKUP ----------

def _get_subordinates(user: 'User'):
    """User'ning to'g'ridan-to'g'ri bo'ysunuvchilarini qaytaradi."""
    return user.subordinates.filter(enabled=True).order_by('first_name')

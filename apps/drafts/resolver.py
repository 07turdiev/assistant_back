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
    # Qatnashuvchi bo'lim/boshqarmalar (har birining boshlig'i tadbirga qo'shiladi)
    participant_directions: list = field(default_factory=list)
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

    # 1. Bo'lim aytilganmi? (tadbir mazmuni — bo'lim boshlig'i qatnashchi bo'lib qo'shiladi)
    target_dept_name = (intent.get('target_department') or '').strip()
    if target_dept_name:
        direction = _resolve_direction(target_dept_name)
        if direction:
            result.target_direction = direction
        else:
            result.warnings.append(f'"{target_dept_name}" — bunday bo\'lim DB\'da topilmadi')

    # 1.5 Bo'lim aniq aytilmagan/topilmagan bo'lsa — MAVZU (sarlavha + tavsif) nomidan
    #     bo'lim/boshqarmalarni DB bilan solishtirib aniqlashga harakat qilamiz.
    #     ("raqamlashtirish va sun'iy intellekt yo'nalishi" → tegishli boshqarma)
    if result.target_direction is None:
        topic = ' '.join(filter(None, [
            intent.get('title') or '',
            intent.get('description') or '',
            target_dept_name,
        ]))
        guessed = _match_direction_from_topic(topic)
        if guessed:
            result.target_direction = guessed
            result.warnings.append(f"Bo'lim mavzudan aniqlandi: {guessed.name_uz}")

    # 1.6 Qatnashuvchi bo'lim/yo'nalishlar ("teatr, konsert yo'nalishlari qatnashsin") —
    #     har birini Direction'ga moslab, qatnashchi bo'limlarga qo'shamiz.
    seen_dir_ids = {result.target_direction.id} if result.target_direction else set()
    for dept_name in (intent.get('participant_departments') or []):
        dept_clean = (dept_name or '').strip()
        if not dept_clean:
            continue
        d = _resolve_direction(dept_clean)
        if d is None:
            d = _match_direction_from_topic(dept_clean)
        if d and d.id not in seen_dir_ids:
            result.participant_directions.append(d)
            seen_dir_ids.add(d.id)
        elif d is None:
            result.warnings.append(f'"{dept_clean}" — qatnashuvchi bo\'lim DB\'da topilmadi')

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

    # 3. Qoralamani KO'RIB TASDIQLOVCHI = yuboruvchining yordamchisi (YORDAMCHI).
    #    Yordamchi bo'lmasa — yuboruvchining o'zi ko'rib joylashtiradi.
    assistant = _find_assistant(sender)
    result.assigned_to = assistant or sender

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

    # 2. Substring (qisqa kalit so'z uchun: "teatr" → "Teatr va sirk ... bo'limi")
    direction = Direction.objects.filter(
        Q(name_uz__icontains=name_clean) | Q(name_ru__icontains=name_clean)
    ).first()
    if direction:
        return direction

    # 3. So'z-balansli moslik — ko'p so'zli, agglutinativ (qo'shimchali) nomlar uchun ENG ishonchli.
    #    Apostrof/affiks farqlariga chidamli: "raqamlashtirish va sun'iy intellekt" →
    #    "Raqamlashtirish va sun'iy intellektni rivojlantirish boshqarmasi".
    word_match = _best_direction_by_words(name_clean)
    if word_match:
        return word_match

    # 4. Char-fuzzy — oxirgi chora (imlo/STT xatosi uchun)
    from apps.core.fuzzy import best_match
    all_dirs = list(Direction.objects.all())
    return (
        best_match(name_clean, all_dirs, key=lambda d: d.name_uz, threshold=0.5)
        or best_match(name_clean, all_dirs, key=lambda d: d.name_ru, threshold=0.5)
    )


# Bo'lim/boshqarma nomlaridagi umumiy/ahamiyatsiz so'zlar — mavzu solishtirishda e'tiborsiz
_DIR_STOPWORDS = {
    'va', 'bilan', 'uchun', 'bolim', "bo'lim", "bo'limi", 'bolimi', 'boshqarma',
    'boshqarmasi', 'departament', 'departamenti', 'sektor', 'sektori', 'markaz',
    'markazi', 'bosh', 'general', 'rivojlantirish', 'masalalari', 'masala',
    'ishlari', 'ish', 'yonalishi', "yo'nalishi", 'yonalish', "yo'nalish", 'soha',
    'sohasi', 'boyicha', "bo'yicha", 'va', 'hamda', 'tashkil', 'qilish', 'nazorat',
    'tahlil', 'xizmati', 'xizmat', 'guruhi', 'guruh', 'qoshma',
}


def _word_hits(a_words: list[str], b_words: list[str]) -> int:
    """`a_words` dan nechtasi `b_words` ichida bor (aniq yoki uzun so'z substringi)."""
    hits = 0
    for w in a_words:
        for t in b_words:
            if w == t or ((len(w) >= 5 or len(t) >= 5) and (w in t or t in w)):
                hits += 1
                break
    return hits


def _dir_words(text: str) -> list[str]:
    """Matnni ma'noli so'zlarga ajratadi (stopword va qisqa so'zlarsiz)."""
    from apps.core.fuzzy import _norm
    return [w for w in _norm(text).split() if len(w) > 2 and w not in _DIR_STOPWORDS]


def _best_direction_by_words(query: str) -> 'Direction | None':
    """Bo'lim NOMI/iborasini so'z-balansli moslik bilan Direction'ga moslaydi.

    Ham query qamrovi (query so'zlari nomda bor), ham nom qamrovi (nom so'zlari queryda bor)
    hisoblanadi va F1 (garmonik o'rta) olinadi — shunda qisqa nomlar ("Sun'iy intellekt bo'limi")
    to'liqroq nomdan ("...sun'iy intellektni rivojlantirish boshqarmasi") asossiz ustun kelmaydi.
    """
    from apps.directions.models import Direction

    q_words = _dir_words(query)
    if not q_words:
        return None
    best = None
    best_score = 0.0
    for d in Direction.objects.all():
        n_words = _dir_words(d.name_uz)
        if not n_words:
            continue
        q_cov = _word_hits(q_words, n_words) / len(q_words)
        n_cov = _word_hits(n_words, q_words) / len(n_words)
        if q_cov + n_cov == 0:
            continue
        f1 = 2 * q_cov * n_cov / (q_cov + n_cov)
        if f1 > best_score:
            best_score = f1
            best = d
    return best if best_score >= 0.5 else None


def _match_direction_from_topic(topic: str) -> 'Direction | None':
    """Bo'lim aniq aytilmaganda — tadbir MAVZUSIDAN (sarlavha/tavsif) bo'limni topadi.

    Har bir Direction nomidagi MA'NOLI so'zlar (stopwordsdan tashqari) mavzuda
    qanchalik uchrashini hisoblaydi. Eng ko'p mos kelgan (>=50%) bo'limni qaytaradi.
    Substring mosligi ham hisoblanadi ("intellekt" -> "intellektni").
    """
    from apps.core.fuzzy import _norm
    from apps.directions.models import Direction

    if not topic or not topic.strip():
        return None
    topic_words = {w for w in _norm(topic).split() if len(w) > 2}
    if not topic_words:
        return None

    best = None
    best_score = 0.0
    for d in Direction.objects.all():
        name_words = [
            w for w in _norm(d.name_uz).split()
            if len(w) > 2 and w not in _DIR_STOPWORDS
        ]
        if not name_words:
            continue
        hits = 0
        for w in name_words:
            for tw in topic_words:
                # Qisqa so'zlar — faqat aniq moslik; uzun so'zlar — substring ham (intellekt→intellektni)
                if w == tw or (len(w) >= 5 and (w in tw or tw in w)):
                    hits += 1
                    break
        score = hits / len(name_words)
        # Ko'p so'zli bo'lim — kamida 2 ta moslik; bir so'zli — 1 ta yetarli
        min_hits = 2 if len(name_words) >= 2 else 1
        if score > best_score and hits >= min_hits:
            best_score = score
            best = d
    return best if best_score >= 0.5 else None


def _find_head_of_direction(direction: 'Direction') -> 'User | None':
    """Bo'limning ma'sul shaxsi — avval `Direction.head`, bo'lmasa BOSHLIQ rolidagi xodim."""
    head = getattr(direction, 'head', None)
    if head and head.enabled:
        return head
    from apps.users.enums import RoleName
    from apps.users.models import User
    return User.objects.filter(
        direction=direction,
        role__name=RoleName.BOSHLIQ,
        enabled=True,
    ).first()


def _find_assistant(sender: 'User') -> 'User | None':
    """Yuboruvchining yordamchisi (YORDAMCHI, chief=sender) — qoralamani ko'rib tasdiqlovchi."""
    from apps.users.enums import RoleName
    from apps.users.models import User
    return User.objects.filter(
        chief=sender, role__name=RoleName.YORDAMCHI, enabled=True,
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
        User.objects.filter(role__name=RoleName.BOSHLIQ, enabled=True).order_by('last_name', 'first_name')
    )


# ---------- USER NAME FUZZY MATCH ----------

def _resolve_user_names(names: list[str]) -> tuple[list, list[str]]:
    """Ismlar ro'yxatini User obyektlariga moslaydi.

    Returns:
        (matched_users, unmatched_names) — moslangan User'lar va moslanmagan ismlar
    """
    from apps.core.fuzzy import best_match
    from apps.users.models import User

    matched: list = []
    unmatched: list[str] = []
    seen_user_ids = set()

    # Fuzzy fallback uchun (lazy yuklanadi — aniq mos topilmagan ismlar uchungina)
    all_users: list | None = None

    def _full_name(u) -> str:
        return ' '.join(filter(None, [u.last_name, u.first_name, u.father_name]))

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
                # Fuzzy — foizli o'xshashlik bo'yicha eng yaqin foydalanuvchi (imlo/STT xatosi uchun)
                if all_users is None:
                    all_users = list(User.objects.filter(enabled=True))
                fz = best_match(name_clean, all_users, key=_full_name, threshold=0.5)
                if fz and fz.id not in seen_user_ids:
                    matched.append(fz)
                    seen_user_ids.add(fz.id)
                else:
                    unmatched.append(name_clean)

    return matched, unmatched


# ---------- SUBORDINATE LOOKUP ----------

def _get_subordinates(user: 'User'):
    """User'ning to'g'ridan-to'g'ri bo'ysunuvchilarini qaytaradi."""
    return user.subordinates.filter(enabled=True).order_by('first_name')

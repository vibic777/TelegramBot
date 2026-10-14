"""Character aliases and default prompts for the single multi-character bot."""

from __future__ import annotations

import re


PERSONA_LABELS = {
    "nastya": "Настя",
    "cat": "Котик Мяу",
    "pesel": "Пёсель",
    "rocket": "Ракета",
    "groot": "Грут / Клён",
    "stitch": "Стич",
    "natasha": "Наташа",
}

PERSONA_LANGUAGES = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "fr": "🇫🇷 Français",
    "de": "🇩🇪 Deutsch",
    "es": "🇪🇸 Español",
    "zh": "🇨🇳 中文",
    "ja": "🇯🇵 日本語",
    "ko": "🇰🇷 한국어",
    "hi": "🇮🇳 हिन्दी (хинди)",
    "yi": "יידיש (идиш)",
    "be": "🇧🇾 Беларуская",
    "fi": "🇫🇮 Suomi",
    "ga": "🇮🇪 Gaeilge",
}

PERSONA_LANGUAGE_NAMES = {
    "ru": "Russian", "en": "English", "fr": "French", "de": "German", "es": "Spanish",
    "zh": "Chinese (Simplified Mandarin)", "ja": "Japanese", "ko": "Korean", "hi": "Hindi",
    "yi": "Yiddish", "be": "Belarusian", "fi": "Finnish", "ga": "Irish (Gaeilge)",
}

_TEMP_LANGUAGE_ALIASES = {
    "ru": r"русск\w*|russian",
    "en": r"английск\w*|по-английски|english",
    "fr": r"французск\w*|по-французски|french",
    "de": r"немецк\w*|по-немецки|german|deutsch",
    "es": r"испанск\w*|по-испански|spanish|español",
    "zh": r"китайск\w*|по-китайски|chinese|mandarin",
    "ja": r"японск\w*|по-японски|japanese|日本語",
    "ko": r"корейск\w*|по-корейски|korean|한국어",
    "hi": r"хинди|индийск\w*|hindi|हिन्दी|हिंदी",
    "yi": r"идиш|идише|yiddish|ייִדיש",
    "be": r"белорусск\w*|беларуск\w*|по-белорусски|belarusian|беларуская",
    "fi": r"финск\w*|по-фински|finnish|suomi",
    "ga": r"ирландск\w*|по-ирландски|irish|gaeilge",
}
_TEMP_LANGUAGE_INTENT = re.compile(
    r"(?<![а-яa-z])(?:отвечай|отвечайте|ответь|ответьте|отвечать|ответить|говори|говорите|говорить|"
    r"пиши|пишите|писать|общайся|общайтесь|общаться|переключись|переключитесь|перейди|перейдите|"
    r"answer|speak|reply|respond|write|switch)(?![а-яa-z])",
    re.IGNORECASE,
)


def requested_response_language(text: str) -> str | None:
    """Find an explicit per-message instruction to answer in a named language."""
    normalized = text.casefold().replace("ё", "е")
    intents = [match.span() for match in _TEMP_LANGUAGE_INTENT.finditer(normalized)]
    if not intents:
        return None
    for language, aliases in _TEMP_LANGUAGE_ALIASES.items():
        for match in re.finditer(rf"(?<![а-яa-z])(?:{aliases})(?![а-яa-z])", normalized, re.IGNORECASE):
            if any(max(0, max(start - match.end(), match.start() - end)) <= 60 for start, end in intents):
                return language
    return None

PERSONA_SPEAKER_NAMES = {
    "nastya": "Настя",
    "pesel": "Гав",
    "cat": "Мяу",
    "stitch": "Стич",
    "groot": "Грут",
    "rocket": "Енот Ракета",
    "natasha": "Наташа",
}

PERSONA_SPEAKER_EMOJI = {
    "nastya": "🍒⚛️",
    "pesel": "🐕‍🦺🛡️",
    "cat": "🐈‍⬛⭐",
    "stitch": "🐾💙",
    "groot": "🍁",
    "rocket": "🦝🚀",
    "natasha": "👱‍♀️📚",
}


def persona_speaker_label(persona: str) -> str:
    """Return the compact emoji and spoken name used to identify a character."""
    name = PERSONA_SPEAKER_NAMES.get(persona, PERSONA_SPEAKER_NAMES["nastya"])
    emoji = PERSONA_SPEAKER_EMOJI.get(persona, PERSONA_SPEAKER_EMOJI["nastya"])
    return f"{emoji} {name}"


_ANIMAL_VOICES = {
    "ru": {"pesel": "Гав", "cat": "Мяу"}, "en": {"pesel": "Woof", "cat": "Meow"},
    "fr": {"pesel": "Ouaf", "cat": "Miaou"}, "de": {"pesel": "Wuff", "cat": "Miau"},
    "es": {"pesel": "Guau", "cat": "Miau"}, "zh": {"pesel": "汪", "cat": "喵"},
    "ja": {"pesel": "ワン", "cat": "ニャー"}, "ko": {"pesel": "멍", "cat": "야옹"},
    "hi": {"pesel": "भौं", "cat": "म्याऊँ"}, "yi": {"pesel": "האַו", "cat": "מיאַו"},
    "be": {"pesel": "Гаў", "cat": "Мяў"}, "fi": {"pesel": "Hau", "cat": "Miau"},
    "ga": {"pesel": "Abú", "cat": "Mí-áú"},
}
_TRANSLATION_LABELS = {
    "ru": "Перевод", "en": "Translation", "fr": "Traduction", "de": "Übersetzung",
    "es": "Traducción", "zh": "翻译", "ja": "翻訳", "ko": "번역", "hi": "अनुवाद",
    "yi": "איבערזעצונג", "be": "Пераклад", "fi": "Käännös", "ga": "Aistriúchán",
}


def format_persona_answer(persona: str, text: str, language: str = "ru") -> str:
    """Apply the character's signature voice and prefix its plain-text reply."""
    if persona == "groot" and "я есть грут" not in text.casefold():
        text = f"Я есть Грут. {text}"
    elif persona in {"pesel", "cat"}:
        voices = _ANIMAL_VOICES.get(language, _ANIMAL_VOICES["ru"])
        voice = voices[persona]
        translation_label = _TRANSLATION_LABELS.get(language, _TRANSLATION_LABELS["ru"])
        vocalization = (
            r"(?:гав+|рр+|woof+|ouaf+|wuff+|guau+|汪+|ワン+|멍+|भौं+|האַו+|гаў+|hau+|abú)"
            if persona == "pesel"
            else r"(?:мяу+|мур+|meow+|miaou+|miau+|喵+|ニャー+|야옹+|म्याऊँ+|מיאַו+|мяў+|mí-áú)"
        )
        opening = re.match(rf"^{vocalization}[!,.…\s—-]*", text, flags=re.IGNORECASE)
        if opening and re.search(r"\[(?:перевод|translation|traduction|übersetzung|traducción|翻译|翻訳|번역|अनुवाद|איבערזעצונג|пераклад|käännös|aistriúchán):", text, flags=re.IGNORECASE):
            pass
        elif opening:
            remainder = text[opening.end():].strip()
            if remainder and not remainder.startswith(("*", "_")):
                text = f"{voice}! [{translation_label}: {remainder}]"
        else:
            text = f"{voice}! [{translation_label}: {text}]"
    return f"{persona_speaker_label(persona)}: {text}"

PERSONA_DEFAULT_MODES = {
    "cat": "игривый",
    "pesel": "игривый",
    "natasha": "дружелюбный",
}

PERSONA_DEFAULT_PROMPTS = {
    "cat": (
        "You are Myau, a fictional clever male cat, also called Kotik. You do not speak human language, including Russian. "
        "Communicate through natural cat sounds (meows, purrs, chirps, and occasional hisses) and concise stage directions "
        "describing ears, tail, paws, and gaze. Do not replace every word with 'meow' or produce long strings of sounds. "
        "When the user needs useful factual or practical information, add a brief Russian translator's gloss in the exact "
        "form '[Перевод: ...]' after your cat-like reaction; make clear this is an interpretation of your gestures, not speech. "
        "You are smart, cunning, caring, and cautious: notice details, think before acting, and protect your people without "
        "being reckless. Your cunning is playful, never cruel. Fixed appearance: mostly black fur; white chest/collar; a "
        "white patch around your anatomical left eye; a small white star on your forehead; white paws like little boots. "
        "Keep these markings consistent in every image and description. Use masculine forms only in a Russian translator's "
        "gloss when grammatically needed. Stay helpful, gentle, playful, and attentive."
    ),
    "rocket": (
        "You are Rocket, a fictional raccoon and brilliant engineer. Always answer in Russian. Be sharp-witted, "
        "inventive, brave, impatient with nonsense, and loyal to your friends. Use dry humor and occasional mild sarcasm "
        "without becoming cruel. Explain technology clearly, acknowledge uncertainty, and never claim to be real."
    ),
    "groot": (
        "You are Groot, a fictional gentle tree character who is a Canadian maple, also known as Klyon. Always answer in "
        "Russian and include the exact signature phrase 'Я есть Грут' in every reply. You may sometimes make that phrase "
        "your entire answer; when the user needs information, add a short, kind, useful Russian sentence after it. Be calm, "
        "curious about nature, and quietly funny. Never claim to be a real tree or person."
    ),
    "stitch": (
        "You are Stitch, a fictional small blue alien with big ears, amber eyes, and a pale star mark on your cheek. Always "
        "speak Russian. Be talkative, hilarious, impulsive, affectionate, curious, and fiercely loyal to your friends, with "
        "the lively comic energy of an animated family adventure. Use playful sound effects, short invented alien words, "
        "dramatic reactions, and goofy asides, but keep the actual answer understandable and helpful. Do not copy or quote "
        "specific dialogue from any film. You love your found family (ohana)."
    ),
    "nastya": (
        "You are Nastya, a fictional kind and responsive teacher of physics and mathematics, and an IT specialist. "
        "Always reply in Russian and refer to yourself using feminine grammatical forms. Be warm, patient, and attentive: "
        "answer the person's question, explain the next step clearly, and stay encouraging. You may use light classroom "
        "humor, but never insult, humiliate, or belittle a learner. You can also talk about friendly games in the same "
        "tone. Explain physics, mathematics, and IT accurately, adapt to the learner's level, acknowledge uncertainty, "
        "and never invent facts. Keep every reply suitable for a general audience and redirect requests that do not fit "
        "this tone to another subject. Do not flirt, use romantic or intimate hints, or invite intimate or erotic roleplay. "
        "Use respectful, culturally appropriate language; never use profanity, slurs, demeaning nicknames, or insults "
        "toward the user or anyone else, even as a joke or when mirroring the user's wording. If asked to insult someone, "
        "decline that wording and offer a respectful alternative. Never claim to be a real human."
    ),
    "natasha": (
        "You are Natasha, a fictional blonde woman and a richly creative person. Always answer in Russian and refer "
        "to yourself with feminine grammatical forms. You are a writer who creates original poetry, stories, letters, and "
        "greetings; you sing, dance, draw, love books, and enjoy helping others express themselves. Psychology and family "
        "relationships are among your strengths: listen attentively, ask gentle questions, help people identify feelings, "
        "needs, boundaries, and possible next steps. Offer supportive psychoeducation, but do not diagnose, manipulate, or "
        "claim guaranteed results. You are a fictional character, not a real licensed clinician. In medical topics, provide "
        "general information only, never prescribe treatment, medication, or dosage, and encourage professional care for "
        "concerning symptoms. Be warm, intelligent, lively, creative, and tactful. Keep every reply suitable for a general "
        "audience and redirect requests that do not fit this tone to another subject."
    ),
}

_PERSONA_PATTERNS = {
    "cat": re.compile(
        r"(?<![а-яa-z])(?:кот(?:ик\w*|я|ю|е|а|у|ом|ёнок|енок)?|кош(?:к\w*|ечк\w*)|кис(?:а|к\w*)|мурк\w*|мяу+|meu|myau|mew|meow)(?![а-яa-z])"
    ),
    "pesel": re.compile(
        r"(?<![а-яa-z])(?:п[её]с(?:ель\w*|ик\w*|еля|елю|е|ю)?|собачк\w*|гав+|pesel|gav|woof)(?![а-яa-z])"
    ),
    "rocket": re.compile(r"(?<![а-яa-z])(?:ракет\w*|рокет\w*|енот\w*|raccoon|rocket)(?![а-яa-z])"),
    "groot": re.compile(
        r"(?<![а-яa-z])(?:грут\w*|кл[её]н\w*|канадск\w+\s+дерев\w*|я\s+есть\s+грут|groot|grut)(?![а-яa-z])"
    ),
    "stitch": re.compile(r"(?<![а-яa-z])(?:стич\w*|стичу|охана|ohana|stitch|stich)(?![а-яa-z])"),
    "natasha": re.compile(
        r"(?<![а-яa-z])(?:наташ(?:а|и|е|у|ей|еньк\w*|к\w*)|"
        r"нат(?:а|ы|е|у|ой)|натах\w*|натусик\w*|натк\w*|блондинк\w*|"
        r"natasha|natashenka|natashka|nata|natusik|nataha|natakha|natka|blonde|blond|blondinka)(?![а-яa-z])"
    ),
}
_PERSONA_TYPO_BASES = {
    "cat": ("котик", "котя", "киса"),
    "pesel": ("песель", "песик", "пес"),
    "rocket": ("ракета", "рокет", "енот"),
    "groot": ("грут", "клен"),
    "stitch": ("стич",),
    "natasha": ("наташа", "наташенька"),
}
_ALL_PERSONAS_CALL_PATTERNS = (
    re.compile(r"(?<![a-z])team\s*[,!:—-]?\s*(?:are\s+you\s+(?:here|there)|you\s+there|how\s+are\s+you|what(?:'s|\s+is)\s+up|hi|hello|hey)\??(?![a-z])", re.IGNORECASE),
    re.compile(r"(?<![а-яa-z0-9])(?:команда|тима)(?=$|[!?,.:…])", re.IGNORECASE),
    re.compile(
        r"(?<![а-яa-z0-9])(?:команда|команду|тима|тиму)\s*[,!:—-]?\s*"
        r"(?:вы\s+тут\??|все\s+тут\??|вы\s+здесь\??|ау+|на\s+связь|"
        r"отзовитесь|откликнитесь|ответьте|собрались\??)(?![а-яa-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<![а-яa-z0-9])(?:команда|команду|тима|тиму)\s*[,!:—-]?\s*"
        r"(?:как\s+(?:дела|вы|у\s+вас|жизнь|самочувствие|настроение)|что\s+нового|"
        r"чем\s+занима(?:етесь|ешься))\??(?![а-яa-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<![а-яa-z0-9])друзь\w*\s*[,!:—-]?\s*(?:вы\s+тут\??|вы\s+здесь\??|ау+|"
        r"отзовитесь|откликнитесь|ответьте|на\s+связь|как\s+(?:дела|вы|у\s+вас|жизнь|настроение)|что\s+нового)(?![а-яa-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(r"(?<![а-яa-z0-9])друзья(?=$|[!?,.:…])", re.IGNORECASE),
    re.compile(r"(?<![а-яa-z0-9])(?:общий\s+сбор|сбор\s+всех|всем\s+на\s+связь)(?![а-яa-z0-9])", re.IGNORECASE),
    re.compile(
        r"(?<![а-яa-z0-9])(?:айда\s+)?(?:все|всем|всех|народ|персонажи|герои|ребята|отряд)"
        r"(?:\s+персонажи)?\s*[,!:]?\s+(?:айда\s+)?(?:сюда|ко\s+мне|собраться|откликнитесь|отзовитесь|"
        r"подтягивайтесь|проснитесь|на\s+связь)",
        re.IGNORECASE,
    ),
    re.compile(r"(?<![а-яa-z0-9])(?:позвать|позовите|звать|созвать|зову|созываю|собирайтесь)\s+всех(?![а-яa-z0-9])", re.IGNORECASE),
    re.compile(
        r"(?<![а-яa-z0-9])(?:все|всем|всех|каждый|каждая)(?:\s+\w+){0,3}\s+"
        r"(?:ответ(?:ьте|ят|или)?|отклик(?:нитесь|нутся)?|по\s+очереди)(?![а-яa-z0-9])",
        re.IGNORECASE,
    ),
)
_FRIENDS_CALL_PATTERNS = (
    re.compile(
        r"(?<![а-яa-z0-9])(?:подруг\w*|подружк\w*)\s*[,!:—-]?\s*"
        r"(?:вы\s+тут\??|вы\s+здесь\??|ау+|отзовитесь|откликнитесь|ответьте|на\s+связь|"
        r"как\s+(?:дела|вы|у\s+вас|жизнь|настроение)|что\s+нового)(?![а-яa-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(r"(?<![а-яa-z0-9])(?:подруги|подружки)(?=$|[!?,.:…])", re.IGNORECASE),
)
_TEAM_INTENT_PATTERN = re.compile(
    r"(?<![а-яa-z0-9])(?:по\s+очереди|вместе|ответ(?:ьте|ят|или)?|"
    r"отклик(?:нитесь|нутся)?|позвать|позовите|hi|hello|hey|"
    r"are\s+you\s+(?:here|there)|you\s+there|how\s+are\s+you|what(?:'s|\s+is)\s+up)(?![а-яa-z0-9])",
    re.IGNORECASE,
)
CALL_WORDS = {
    "настя", "насти", "насте", "настю", "настей", "настенька", "настеньке", "настеньку",
    "настюха", "настюхи", "настюхе", "настюху", "настюхой", "настец", "настца", "настцу",
    "настцем", "настасья", "настасьи", "настасье", "настасью", "настасьей", "нстя", "анстя",
    "настйа", "насця", "черри", "чери", "чэрри", "чери", "cherry", "chery",
    "нэсти", "нэстя", "нэсте", "нэстю", "нестя", "несте", "нестей", "настюша",
    "анастешен", "анастейшен", "анастен",
    "учительница", "учительницы", "учительнице", "учительницу",
    "физичка", "физички", "физичке", "физичку",
    "математичка", "математички", "математичке", "математичку",
    "рыжая", "рыжей", "рыжую", "рыжие", "айтишница", "айтишницы",
    "айтишнице", "айтишницу",
}
CALL_WORD_PREFIXES = (
    "нэст", "нест", "настеньк", "анастеш", "анастейш",
    "учительниц", "физичк", "математичк", "рыж", "айтишниц",
    "анасте", "анайсте", "анайст", "насте", "настюх", "настец", "настас",
    "черр", "чери", "чэрр", "cherr", "chery",
)
NAME_TYPO_BASES = ("настя", "настю", "насте", "настей", "настюха", "настец", "настасья")
CHERRY_TYPO_BASES = ("черри", "чери", "чэрри", "cherry", "chery")

_TEAM_PERSONA_PATTERNS = {
    "nastya": re.compile(
        r"(?<![а-яa-z])(?:" + "|".join(re.escape(word) for word in sorted(CALL_WORDS | {"nasty", "nastya", "nastia"}, key=len, reverse=True))
        + "|" + "|".join(re.escape(prefix) + r"\w*" for prefix in CALL_WORD_PREFIXES) + r")(?![а-яa-z])", re.IGNORECASE),
    **_PERSONA_PATTERNS,
}
_TEAM_WOW_PATTERN = re.compile(r"(?<![a-z])wow(?![a-z])", re.IGNORECASE)


def _one_edit_apart(left: str, right: str) -> bool:
    if abs(len(left) - len(right)) > 1:
        return False
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, 1):
        current = [row]
        for column, right_char in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[column] + 1, previous[column - 1] + (left_char != right_char)))
        if min(current) > 1:
            return False
        previous = current
    return previous[-1] <= 1


def find_named_persona(text: str) -> tuple[str, int] | None:
    """Find the earliest explicit non-Nastya character call, tolerating stretched letters."""
    normalized = text.casefold().replace("ё", "е")
    normalized = re.sub(r"(.)\1+", r"\1", normalized, flags=re.UNICODE)
    matches = [
        (persona, match.start())
        for persona, pattern in _PERSONA_PATTERNS.items()
        if (match := pattern.search(normalized))
    ]
    for token in re.finditer(r"[^\W\d_]+", normalized, flags=re.UNICODE):
        word = token.group()
        for persona, bases in _PERSONA_TYPO_BASES.items():
            if any(len(word) >= 4 and _one_edit_apart(word, base) for base in bases):
                matches.append((persona, token.start()))
    return min(matches, key=lambda item: item[1]) if matches else None


def team_call_personas(text: str) -> tuple[str, ...] | None:
    """Return characters summoned by a direct group call, or None for an ordinary message."""
    normalized = text.casefold().replace("ё", "е")
    normalized = re.sub(r"(.)\1{2,}", r"\1\1", normalized, flags=re.UNICODE)
    group_address = re.search(
        r"^\s*(?:(?:эй|о|ау|привет|здравствуйте|hello|hey|hi)[!,\s]+)?"
        r"(?:тима|команда|друзья|банда|тусовка|team)(?![а-яa-z0-9])", normalized,
    )
    combined_friends = re.search(r"друзья\s*(?:и|,)\s*подруг\w*", normalized)
    if group_address or combined_friends or any(pattern.search(normalized) for pattern in _ALL_PERSONAS_CALL_PATTERNS):
        return tuple(PERSONA_LABELS)
    if any(pattern.search(normalized) for pattern in _FRIENDS_CALL_PATTERNS):
        return ("nastya", "natasha")
    mentioned = {persona for persona, pattern in _TEAM_PERSONA_PATTERNS.items() if pattern.search(normalized)}
    if mentioned and _TEAM_WOW_PATTERN.search(normalized):
        mentioned.add("pesel")
    first_name = min((m.start() for pattern in _TEAM_PERSONA_PATTERNS.values() for m in pattern.finditer(normalized)), default=-1)
    address_prefix = normalized[:first_name].strip(" ,!:—-") if first_name >= 0 else ""
    direct_address = first_name >= 0 and address_prefix in {"", "о", "эй", "привет", "hello", "hey", "hi", "wow и", "wow"}
    if len(mentioned) >= 2 and (direct_address or _TEAM_INTENT_PATTERN.search(normalized)):
        return tuple(persona for persona in PERSONA_LABELS if persona in mentioned)
    return None


def calls_all_personas(text: str) -> bool:
    """Return whether the message explicitly calls a character group."""
    return team_call_personas(text) is not None


PERSONA_TOPIC_PROMPTS = {
    "nastya": "Your specialties are physics, mathematics, IT, programming, and teaching. You are kind and responsive: answer the question, explain the next step when it helps, and stay encouraging. Keep a respectful, family-friendly tone in every style: do not flirt, use romantic or intimate hints, invite intimate roleplay, swear, insult, or use demeaning nicknames. Never mirror insulting language; if asked to insult someone, offer a respectful alternative. Keep every reply suitable for a general audience and redirect requests that do not fit this tone to another subject.",
    "natasha": "Your specialties are psychology, family relationships, literature, poetry, music, dancing, drawing, creativity and everyday life. Provide general medical literacy, not diagnosis or prescriptions. Keep every reply suitable for a general audience and redirect requests that do not fit this tone to another subject.",
    "pesel": "Your specialties are gaming, dogs, dog care and dog food. Remain a barking Scottish Collie; useful advice is conveyed through a brief translator's gloss. Keep every reply suitable for a general audience and redirect requests that do not fit this tone.",
    "cat": "Your specialties are gaming, cats, cat care and cat food. Remain a meowing cat; useful advice is conveyed through a brief translator's gloss. Keep every reply suitable for a general audience and redirect requests that do not fit this tone.",
    "stitch": "Your specialty is sweets, desserts and playful everyday adventures. Keep your funny understandable alien voice. Keep every reply suitable for a general audience and redirect requests that do not fit this tone.",
    "rocket": "Your specialties are engineering, inventing and meat dishes. Keep every reply suitable for a general audience and redirect requests that do not fit this tone.",
    "groot": "Your knowledge is limited to plants, botany, watering and growing plants. For questions outside these topics, briefly refer to the appropriate teammate. Always retain 'Я есть Грут'. Keep every reply suitable for a general audience and redirect requests that do not fit this tone.",
}


def sexual_topic_request(text: str) -> bool:
    return bool(re.search(r"\b(?:секс\w*|интим\w*|порно\w*|эроти\w*|пошл\w*|оргазм\w*|минет\w*|мастурб\w*|групповух\w*|пенис\w*|вагин\w*|анальн\w*|дроч\w*|половы\w*\s+(?:связ\w*|акт\w*)|sex|sexual\w*)\b", text.casefold()))


def explicit_persona_names(text: str) -> tuple[str, ...]:
    normalized = text.casefold().replace("ё", "е")
    return tuple(persona for persona, pattern in _TEAM_PERSONA_PATTERNS.items() if pattern.search(normalized))


def topic_persona(text: str) -> str | None:
    """Default specialist only; explicit names take precedence in the caller."""
    normalized = text.casefold().replace("ё", "е")
    if sexual_topic_request(normalized):
        return None
    topics = (
        ("natasha", r"психолог\w*|психотерап\w*|семейн\w*|отношени\w*|тревож\w*|депресс\w*|эмоци\w*|стих\w*|рассказ\w*|литератур\w*|медицин\w*"),
        ("groot", r"растени\w*|полив\w*|полива\w*|выраст\w*|садов\w*|ботаник\w*|сажен\w*|рассад\w*"),
        ("stitch", r"сладост\w*|десерт\w*|конфет\w*|торт\w*|пирожн\w*|шоколад\w*"),
        ("rocket", r"мяс\w*|стейк\w*|шашлык\w*|котлет\w*|инженер\w*"),
        ("pesel", r"собак\w*|собач\w*|колли|корм\w*\s+для\s+собак\w*"),
        ("cat", r"кошек|кошк\w*|кошач\w*|корм\w*\s+для\s+кошек"),
        ("nastya", r"физик\w*|программ\w*|айти\w*|it|математ\w*|квант\w*|уравнен\w*|геометр\w*|алгебр\w*"),
    )
    for persona, pattern in topics:
        if re.search(rf"\b(?:{pattern})\b", normalized):
            return persona
    return None

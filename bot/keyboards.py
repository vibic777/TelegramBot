from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.personas import PERSONA_LABELS as PERSONAS, PERSONA_LANGUAGES

MODES = {
    "обычный": "Обычный",
    "нормальный": "Нормальный",
    "дружелюбный": "Дружелюбный",
    "игривый": "Игривый",
    "радостный": "Радостный",
    "грустный": "Грустный",
    "весёлый": "Весёлый",
    "печальный": "Печальный",
    "серьёзный": "Серьёзный",
    "вдумчивый": "Вдумчивый",
    "смешной": "Смешной",
    "хаотичный": "Хаотичный",
    "злой": "Злой",
    "агрессивный": "Агрессивный",
    "пассивный": "Пассивный",
    "пофигизм": "Пофигизм",
    "плакса": "Плакса",
    "спокойный": "Спокойный",
    "заботливый": "Заботливый",
    "романтичный": "Тёплый",
    "застенчивый": "Застенчивый",
    "любопытный": "Любопытный",
    "оптимистичный": "Оптимистичный",
    "пессимистичный": "Пессимистичный",
    "драматичный": "Драматичный",
    "уверенный": "Уверенный",
    "саркастичный": "Саркастичный",
    "дерзкий": "Дерзкий",
    "шутник": "Шутник",
    "рандом": "🎲 Рандом",
}

NASTYA_ONLY_MODES = {
    "учительница": "Учительница",
}


def mode_label(mode: str) -> str:
    if mode == "училка":
        mode = "учительница"
    return MODES.get(mode, NASTYA_ONLY_MODES.get(mode, MODES["обычный"]))

def admin_keyboard(
    current_mode: str,
    group_mode: str,
    selected_model: str = "",
    default_persona: str = "nastya",
    memory_limit: int = 50,
    request_queue_limit: int = 50,
    analysis_memory_limit: int = 100,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить модели LM Studio", callback_data="models")],
            [InlineKeyboardButton(text="🤖 Выбрать модель", callback_data="choose_model")],
            [InlineKeyboardButton(text="🎭 Стиль по умолчанию", callback_data="choose_mode")],
            [InlineKeyboardButton(text="🎭 Характер каждого персонажа", callback_data="choose_persona_mode")],
            [InlineKeyboardButton(text="🌐 Язык каждого персонажа", callback_data="choose_persona_language")],
            [InlineKeyboardButton(text="🧠 Память о пользователях", callback_data="pm:home")],
            [InlineKeyboardButton(text="💬 Контекст каждого персонажа", callback_data="cw:home")],
            [InlineKeyboardButton(text=f"↩️ История ссылок: {memory_limit} сообщений", callback_data="choose_memory_limit")],
            [InlineKeyboardButton(text=f"🔎 Анализ истории: {analysis_memory_limit}/65535", callback_data="choose_analysis_memory_limit")],
            [InlineKeyboardButton(text=f"⏳ Буфер очереди: {request_queue_limit}/65536", callback_data="choose_request_queue_limit")],
            [InlineKeyboardButton(text=f"🗣 Персонаж: {PERSONAS.get(default_persona, 'Настя')}", callback_data="choose_persona")],
            [InlineKeyboardButton(text="📝 Контекст / персонаж", callback_data="edit_prompt")],
            [InlineKeyboardButton(text=f"👥 Групповой режим: {group_mode}", callback_data="toggle_group")],
            [InlineKeyboardButton(text="✅ Кому отвечать", callback_data="allowed_users")],
            [InlineKeyboardButton(text="🖥 Доступ к данным системы", callback_data="allowed_system_users")],
            [InlineKeyboardButton(text="👥 Допустимые группы и каналы", callback_data="allowed_chats")],
            [InlineKeyboardButton(text="🧹 Очистить историю всех чатов", callback_data="clear_all")],
            [InlineKeyboardButton(text="🗒 Notio", callback_data="notio:home")],
            [InlineKeyboardButton(text="📋 Показать настройки", callback_data="status")],
        ]
    )


def memory_limit_keyboard(selected: int) -> InlineKeyboardMarkup:
    options = (10, 20, 30, 50, 75, 100, 150, 200)
    rows = [
        [InlineKeyboardButton(text=("✅ " if value == selected else "") + str(value), callback_data=f"memory_limit:{value}")]
        for value in options
    ]
    rows.append([InlineKeyboardButton(text="↩️ В админку", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def analysis_memory_limit_keyboard(selected: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=("✅ " if value == selected else "") + f"{value} сообщений", callback_data=f"analysis_memory_limit:{value}")]
        for value in (0, 10, 20, 30, 50, 100, 200, 1000, 65535)
    ]
    rows.append([InlineKeyboardButton(text="↩️ В админку", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def request_queue_limit_keyboard(selected: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=("✅ " if value == selected else "") + f"{value} сообщений", callback_data=f"request_queue_limit:{value}")]
        for value in (1, 10, 50, 100, 500, 1000, 5000, 65536)
    ]
    rows.append([InlineKeyboardButton(text="↩️ В админку", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def models_keyboard(models: list[dict[str, str]], selected: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=("✅ " if model["id"] == selected else "") + model["id"][:55],
                callback_data=f"model:{index}",
            )
        ]
        for index, model in enumerate(models[:50])
    ]
    rows.append([InlineKeyboardButton(text="↩️ В админку", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def modes_keyboard(selected: str | None = None, persona: str | None = None) -> InlineKeyboardMarkup:
    available_modes = MODES | (NASTYA_ONLY_MODES if persona == "nastya" else {})
    rows = [
        [InlineKeyboardButton(text=("✅ " if mode == selected else "") + label,
                              callback_data=f"persona_mode:{persona}:{mode}" if persona else f"mode:{mode}")]
        for mode, label in available_modes.items()
    ]
    rows.append([InlineKeyboardButton(text="↩️ К персонажам" if persona else "↩️ В админку",
                                      callback_data="choose_persona_mode" if persona else "admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def persona_modes_keyboard(
    selected_modes: dict[str, str],
    default_mode: str,
    persona_defaults: dict[str, str] | None = None,
) -> InlineKeyboardMarkup:
    persona_defaults = persona_defaults or {}
    rows = [
        [InlineKeyboardButton(
            text=f"{label}: {mode_label(selected_modes.get(persona, persona_defaults.get(persona, default_mode)))}",
            callback_data=f"choose_persona_mode:{persona}",
        )]
        for persona, label in PERSONAS.items()
    ]
    rows.append([InlineKeyboardButton(text="↩️ В админку", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def personas_keyboard(selected: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=("✅ " if key == selected else "") + label, callback_data=f"persona:{key}")]
        for key, label in PERSONAS.items()
    ]
    rows.append([InlineKeyboardButton(text="↩️ В админку", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def persona_languages_keyboard(selected_languages: dict[str, str], persona: str | None = None) -> InlineKeyboardMarkup:
    if persona:
        selected = selected_languages.get(persona, "ru")
        rows = [
            [InlineKeyboardButton(
                text=("✅ " if code == selected else "") + label,
                callback_data=f"persona_language:{persona}:{code}",
            )]
            for code, label in PERSONA_LANGUAGES.items()
        ]
        rows.append([InlineKeyboardButton(text="↩️ К персонажам", callback_data="choose_persona_language")])
    else:
        rows = [
            [InlineKeyboardButton(
                text=f"{label}: {PERSONA_LANGUAGES.get(selected_languages.get(key, 'ru'), PERSONA_LANGUAGES['ru'])}",
                callback_data=f"choose_persona_language:{key}",
            )]
            for key, label in PERSONAS.items()
        ]
        rows.append([InlineKeyboardButton(text="↩️ В админку", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

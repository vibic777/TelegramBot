"""Independent rolling conversation windows for each character."""
from aiogram import F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton as Button, InlineKeyboardMarkup as Keyboard

from bot.personas import PERSONA_LABELS, find_named_persona

DEFAULT_WINDOW = 5
MAX_WINDOW = 65535


def window_messages(messages, limit):
    return messages[-limit:] if limit else []


async def context_window(store, persona):
    value = (await store.get("character_context_windows") or {}).get(persona, DEFAULT_WINDOW)
    try:
        return max(0, min(MAX_WINDOW, int(value)))
    except (TypeError, ValueError):
        return DEFAULT_WINDOW


async def set_context_window(store, persona, limit):
    if persona not in PERSONA_LABELS or not 0 <= limit <= MAX_WINDOW:
        raise ValueError("Invalid character or context window")
    settings = dict(await store.get("character_context_windows") or {})
    settings[persona] = limit
    histories = await store.get("history") or {}
    histories = {
        key: window_messages(events, limit)
        if key.endswith(":" + persona) or (persona == "nastya" and key.count(":") == 1)
        else events
        for key, events in histories.items()
    }
    await store.update_many({"character_context_windows": settings, "history": histories})


def register_context_admin(router, get_store, is_owner):
    @router.message(Command("context_window"))
    async def set_window_command(message):
        if not message.from_user or not await is_owner(message.from_user.id):
            await message.answer("Нет доступа")
            return
        parts = (message.text or "").split()
        try:
            name = " ".join(parts[1:-1])
            found = find_named_persona(name)
            persona = name if name in PERSONA_LABELS else (found[0] if found else None)
            limit = int(parts[-1])
            await set_context_window(get_store(), persona, limit)
        except (ValueError, IndexError, TypeError):
            await message.answer("Формат: /context_window Настя 5. Число от 0 до 65535; 0 отключает контекст.")
            return
        await message.answer(f"{PERSONA_LABELS[persona]}: окно контекста — {limit} сообщений.")

    @router.callback_query(F.data.startswith("cw:"))
    async def window_admin(callback):
        if not await is_owner(callback.from_user.id):
            await callback.answer("Нет доступа", show_alert=True)
            return
        parts = callback.data.split(":")
        store = get_store()
        rows = []
        if parts[1] == "home":
            for persona, label in PERSONA_LABELS.items():
                limit = await context_window(store, persona)
                rows.append([Button(text=f"{label}: {limit}", callback_data=f"cw:{persona}")])
            text = "Окно контекста каждого персонажа. По умолчанию 5 последних сообщений; 0 — выключено."
        else:
            persona = parts[1]
            if persona not in PERSONA_LABELS:
                await callback.answer("Неизвестный персонаж")
                return
            if len(parts) == 3:
                try:
                    await set_context_window(store, persona, int(parts[2]))
                except ValueError:
                    await callback.answer("Допустимо от 0 до 65535", show_alert=True)
                    return
            limit = await context_window(store, persona)
            text = (f"{PERSONA_LABELS[persona]}: {limit} последних сообщений (пользователя и персонажа).\n"
                    "Любое число от 0 до 65535 задаётся командой:\n"
                    f"/context_window {persona} 5\n"
                    "0 отключает историю. Уменьшение окна удаляет лишнюю историю этого персонажа.")
            rows = [[Button(text=("✅ " if n == limit else "") + str(n), callback_data=f"cw:{persona}:{n}")]
                    for n in (0, 1, 5, 10, 20, 50, 100, 1000, 65535)]
            rows.append([Button(text="К персонажам", callback_data="cw:home")])
        rows.append([Button(text="В админку", callback_data="admin")])
        await callback.message.edit_text(text, reply_markup=Keyboard(inline_keyboard=rows), parse_mode=None)
        await callback.answer()

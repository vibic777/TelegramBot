"""Owner-only navigation and paginated inspection of personal memories."""
from aiogram import F
from aiogram.types import InlineKeyboardButton as Button, InlineKeyboardMarkup as Keyboard

from bot.personas import PERSONA_LABELS
from bot.user_memory import load_memories, save_memories, format_memory_facts


def memory_pages(memories, dates, *, persona=None, user_id=None):
    """Paginate admin results without mixing selected users or characters."""
    records = []
    for key, facts in sorted(memories.items()):
        character, _, uid = key.partition(":")
        if character not in PERSONA_LABELS or not uid.isdigit():
            continue
        if persona is not None and character != persona:
            continue
        if user_id is not None and uid != str(user_id):
            continue
        if facts:
            heading = f"{PERSONA_LABELS[character]} — пользователь ID {uid}"
            rendered = format_memory_facts(facts, updated_at=dates.get(key, {}))
            records.append((heading, rendered))
    pages = []
    current = ""
    for heading, facts in records:
        for fact in facts:
            line = "• " + fact + "\n"
            prefix = heading + "\n"
            if not current or prefix not in current:
                line = prefix + line
            if len(current) + len(line) > 3400:
                pages.append(current.rstrip())
                current = prefix + "• " + fact + "\n"
            else:
                current += line
    if current:
        pages.append(current.rstrip())
    return pages or ["Сохранённых записей для выбранного фильтра пока нет."]


def register_memory_admin(router, get_store, is_owner, get_owner_id):
    @router.callback_query(F.data.startswith("pm:"))
    async def memory_admin(callback):
        if not await is_owner(callback.from_user.id):
            await callback.answer("Нет доступа", show_alert=True)
            return
        store = get_store()
        parts = callback.data.split(":")
        action = parts[1]
        personas = await store.get("personal_memory_personas") or {}
        users = await store.get("personal_memory_users") or {}
        memories = await load_memories(store)
        allowed = sorted(set([get_owner_id(), *(await store.get("allowed_users") or [])]))
        if action in ("persona", "pc", "all", "toggle", "uc"):
            await store.set("personal_memory_revision", (await store.get("personal_memory_revision") or 0) + 1)
        rows = []
        text = "Память о пользователях. Запись и использование работают, только если включены и персонаж, и пользователь. По умолчанию всё выключено. Выключение сохраняет записи."
        if action == "view":
            try:
                selected = None if parts[2] == "all" else parts[2]
                uid = None if parts[3] == "all" else int(parts[3])
                page = max(0, int(parts[4]))
                if selected is not None and selected not in PERSONA_LABELS:
                    raise ValueError("Unknown character")
            except (ValueError, IndexError):
                await callback.answer("Некорректный фильтр", show_alert=True)
                return
            pages = memory_pages(memories, await store.get("personal_memory_fact_dates") or {}, persona=selected, user_id=uid)
            page = min(page, len(pages) - 1)
            text = f"Просмотр памяти · {page + 1}/{len(pages)}\n\n" + pages[page]
            nav = []
            if page:
                nav.append(Button(text="← Назад", callback_data=f"pm:view:{parts[2]}:{parts[3]}:{page - 1}"))
            if page + 1 < len(pages):
                nav.append(Button(text="Далее →", callback_data=f"pm:view:{parts[2]}:{parts[3]}:{page + 1}"))
            if nav:
                rows.append(nav)
            if uid is not None:
                rows.append([Button(text="К пользователю", callback_data=f"pm:user:{uid}")])
            if selected:
                rows.append([Button(text="К персонажу", callback_data=f"pm:inspect:{selected}")])
            rows.append([Button(text="К памяти", callback_data="pm:home")])
            await callback.message.edit_text(text, reply_markup=Keyboard(inline_keyboard=rows), parse_mode=None)
            await callback.answer()
            return
        if action in ("persona", "pc"):
            persona = parts[2]
            if persona not in PERSONA_LABELS:
                await callback.answer("Неизвестный персонаж")
                return
            if action == "persona":
                personas[persona] = not personas.get(persona, False)
                await store.set("personal_memory_personas", personas)
            else:
                memories = {k: v for k, v in memories.items() if not k.startswith(persona + ":")}
                await save_memories(store, memories)
            action = "home"
        if action == "all":
            await save_memories(store, {})
            action = "home"
        if action in ("user", "toggle", "uc"):
            uid = int(parts[2])
            if action == "toggle":
                if uid not in allowed:
                    await callback.answer("Пользователь больше не разрешён", show_alert=True)
                    return
                users[str(uid)] = not users.get(str(uid), False)
                await store.set("personal_memory_users", users)
            if action == "uc":
                memories = {k: v for k, v in memories.items() if k.split(":")[-1] != str(uid)}
                await save_memories(store, memories)
            text = f"Пользователь {uid}. Память {'включена' if users.get(str(uid)) else 'выключена'}."
            rows = [[Button(text="Включить / выключить", callback_data=f"pm:toggle:{uid}")],
                    [Button(text="Очистить записи пользователя", callback_data=f"pm:uc:{uid}")]]
            rows.append([Button(text="Вся память о пользователе", callback_data=f"pm:view:all:{uid}:0")])
            rows.extend([[Button(text=f"{label}: {len(memories.get(f'{persona}:{uid}', []))} записей", callback_data=f"pm:view:{persona}:{uid}:0")]
                         for persona, label in PERSONA_LABELS.items()])
        elif action in ("inspect", "pu"):
            persona = parts[2]
            if persona not in PERSONA_LABELS:
                await callback.answer("Неизвестный персонаж")
                return
            text = f"{PERSONA_LABELS[persona]}: просмотр сохранённой памяти."
            rows.append([Button(text="Вся память персонажа", callback_data=f"pm:view:{persona}:all:0")])
            ids = sorted(set(allowed + [int(k.split(":")[-1]) for k in memories if k.startswith(persona + ":")]))
            page = max(0, int(parts[3])) if action == "pu" else 0
            rows.extend([[Button(text=f"Пользователь {uid}: {len(memories.get(f'{persona}:{uid}', []))} записей", callback_data=f"pm:view:{persona}:{uid}:0")]
                         for uid in ids[page * 20:(page + 1) * 20]])
            if page:
                rows.append([Button(text="← Пользователи", callback_data=f"pm:pu:{persona}:{page - 1}")])
            if len(ids) > (page + 1) * 20:
                rows.append([Button(text="Пользователи →", callback_data=f"pm:pu:{persona}:{page + 1}")])
        elif action == "users":
            page = max(0, int(parts[2])) if len(parts) > 2 else 0
            ids = sorted(set(allowed + [int(k.split(":")[-1]) for k in memories]))
            rows = [[Button(text=f"{'✅' if users.get(str(uid)) else '▫️'} {uid}", callback_data=f"pm:user:{uid}")] for uid in ids[page * 20:(page + 1) * 20]]
            if page:
                rows.append([Button(text="← Назад", callback_data=f"pm:users:{page - 1}")])
            if len(ids) > (page + 1) * 20:
                rows.append([Button(text="Далее →", callback_data=f"pm:users:{page + 1}")])
            text = "Пользователи: выберите ID для просмотра, переключения и очистки памяти."
        else:
            for persona, label in PERSONA_LABELS.items():
                rows.append([Button(text=f"{'✅' if personas.get(persona) else '▫️'} {label}", callback_data=f"pm:persona:{persona}"), Button(text="Смотреть", callback_data=f"pm:inspect:{persona}"), Button(text="Очистить", callback_data=f"pm:pc:{persona}")])
            rows.extend([[Button(text="По пользователям", callback_data="pm:users:0")],
                         [Button(text="Посмотреть всю память", callback_data="pm:view:all:all:0")],
                         [Button(text="Очистить всю личную память", callback_data="pm:all")]])
        rows.append([Button(text="К памяти", callback_data="pm:home"), Button(text="В админку", callback_data="admin")])
        await callback.message.edit_text(text, reply_markup=Keyboard(inline_keyboard=rows), parse_mode=None)
        await callback.answer()

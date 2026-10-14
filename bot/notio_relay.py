"""Связь бота с Notio: бот передаёт поручения из Telegram в нужный Notio по коду из 12 символов.

Telegram читает только этот бот (одним ботом может пользоваться только одна программа), а Notio на компьютере
подключается к боту сам: один долгий запрос ждёт новых сообщений, ответы Notio присылает обратно.

* Notio создаёт код из 12 символов (как код связи синхронизации) — Настройки → Помощник → Telegram-бот.
* Владелец бота вводит этот код в /admin → «Notio» (или `/notio_add КОД имя`). Бот хранит только SHA-256 кода;
  Notio с незнакомым кодом бот не пускает.
* Человек пишет боту `/notio КОД` — чат привязывается к этому Notio, сообщение с кодом бот удаляет. Дальше
  `/n поручение`, `/n_undo`, `/n_yes`, `/notio_off`. `/notio КОД поручение` — привязать и сразу отправить.
* Кого слушать, решает сам Notio: знать код мало, человека надо разрешить в Notio.

Между ботом и Notio — обычный HTTP: только этот компьютер (по умолчанию 127.0.0.1) или домашняя сеть / VPN.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from collections import deque
from typing import Any, Awaitable, Callable

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiohttp import web

log = logging.getLogger(__name__)

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LENGTH = 12
STORE_KEY = "notio"
# Сколько ждёт поручение, пока Notio его не забрал, и сколько поручений держится на один Notio.
KEEP_SECONDS = 10 * 60
KEEP_ITEMS = 200
# Notio считается на связи, если спрашивал бот не позже этого.
ONLINE_SECONDS = 120
# Неверные коды от одного человека: после стольких попыток за час бот перестаёт их проверять.
WRONG_TRIES = 5
MESSAGE_CHARS = 4000


def normalize_code(typed: str) -> str:
    """Код в том виде, в котором его сделал Notio: заглавные, похожие буквы заменены, пробелы и дефисы убраны."""
    text = typed.upper().replace("O", "0").replace("I", "1").replace("L", "1")
    return "".join(ch for ch in text if ch in ALPHABET)


def wrong_code_words(typed: str) -> str:
    """Что сказать, если прислали не код из 12 символов. 6 цифр — код другого режима Notio («Notio сам читает бота по ключу»)."""
    where = ("Его показывает Notio: Настройки → Помощник → Telegram-бот → выберите «Через вашу программу-бот (TelegramBot)». "
             "Ключ бота в Notio при этом не вводите: ботом пользуется эта программа.")
    if "".join(ch for ch in typed if not ch.isspace()).isdigit() and len(typed.strip()) == 6:
        return ("Это 6 цифр — код другого режима Notio, «Notio сам читает бота по ключу». Здесь нужен код из 12 символов, "
                "например ABCD-EFGH-JKMN. " + where)
    return "Код Notio — 12 символов, например ABCD-EFGH-JKMN. " + where


def code_hash(code: str) -> str:
    return hashlib.sha256(normalize_code(code).encode("ascii")).hexdigest()


def split_code(args: str) -> tuple[str | None, str]:
    """`КОД поручение` → (код, поручение). Код можно написать одним словом или тремя группами по четыре."""
    words = args.split()
    for count in (1, 3):
        if len(words) >= count:
            code = normalize_code("".join(words[:count]))
            if len(code) == CODE_LENGTH and all(len(normalize_code(w)) == len(w.replace("-", "")) for w in words[:count]):
                return code, " ".join(words[count:])
    return None, args.strip()


class NotioRelay:
    """Связи чатов с Notio и очереди поручений; без Telegram и без сети, чтобы проверяться тестами."""

    def __init__(self, store: Any, clock: Callable[[], float] = time.time) -> None:
        self.store = store
        self.clock = clock
        self.queues: dict[str, deque[dict[str, Any]]] = {}
        self.events: dict[str, asyncio.Event] = {}
        self.next_id: dict[str, int] = {}
        self.seen: dict[str, float] = {}
        self.wrong: dict[int, list[float]] = {}

    async def _data(self) -> dict[str, Any]:
        data = await self.store.get(STORE_KEY) or {}
        data.setdefault("instances", {})
        data.setdefault("links", {})
        return data

    async def instances(self) -> dict[str, dict[str, Any]]:
        return (await self._data())["instances"]

    async def add(self, code: str, name: str = "") -> tuple[bool, str]:
        """Владелец бота вводит код Notio. Возвращает (получилось, слова для владельца)."""
        normal = normalize_code(code)
        if len(normal) != CODE_LENGTH:
            return False, wrong_code_words(code)
        data = await self._data()
        digest = code_hash(normal)
        for key, item in data["instances"].items():
            if item["hash"] == digest:
                return False, f"Этот код уже введён: Notio «{item['name']}»."
        key = digest[:12]
        title = name.strip()[:40] or f"Notio {len(data['instances']) + 1}"
        data["instances"][key] = {"name": title, "hash": digest, "added": int(self.clock())}
        await self.store.set(STORE_KEY, data)
        return True, f"Notio «{title}» добавлен. Теперь Notio может подключиться к боту, а люди — написать /notio КОД."

    async def remove(self, key: str) -> str | None:
        data = await self._data()
        item = data["instances"].pop(key, None)
        if item is None:
            return None
        data["links"] = {chat: inst for chat, inst in data["links"].items() if inst != key}
        await self.store.set(STORE_KEY, data)
        self.queues.pop(key, None)
        return item["name"]

    async def by_code(self, code: str) -> str | None:
        digest = code_hash(code)
        for key, item in (await self.instances()).items():
            if item["hash"] == digest:
                return key
        return None

    def blocked(self, user_id: int) -> bool:
        now = self.clock()
        tries = [t for t in self.wrong.get(user_id, []) if now - t < 3600]
        self.wrong[user_id] = tries
        return len(tries) >= WRONG_TRIES

    async def link(self, chat_id: int, user_id: int, code: str) -> str | None:
        """Привязывает чат к Notio по коду; `None` — код неверный (и попытка засчитана)."""
        if self.blocked(user_id):
            return None
        key = await self.by_code(code)
        if key is None:
            self.wrong.setdefault(user_id, []).append(self.clock())
            return None
        data = await self._data()
        data["links"][str(chat_id)] = key
        await self.store.set(STORE_KEY, data)
        return key

    async def unlink(self, chat_id: int) -> bool:
        data = await self._data()
        if data["links"].pop(str(chat_id), None) is None:
            return False
        await self.store.set(STORE_KEY, data)
        return True

    async def linked(self, chat_id: int) -> str | None:
        key = (await self._data())["links"].get(str(chat_id))
        return key if key in await self.instances() else None

    def online(self, key: str) -> bool:
        return self.clock() - self.seen.get(key, 0) <= ONLINE_SECONDS

    def forward(self, key: str, chat_id: int, user_id: int, name: str, text: str) -> None:
        """Ставит сообщение человека в очередь Notio; Notio заберёт его следующим запросом."""
        queue = self.queues.setdefault(key, deque())
        self._drop_old(queue)
        number = self.next_id.get(key, 0) + 1
        self.next_id[key] = number
        queue.append({"update_id": number, "chat_id": chat_id, "user_id": user_id, "name": name, "text": text, "at": self.clock()})
        while len(queue) > KEEP_ITEMS:
            queue.popleft()
        self.events.setdefault(key, asyncio.Event()).set()

    def _drop_old(self, queue: deque[dict[str, Any]]) -> None:
        now = self.clock()
        while queue and now - queue[0]["at"] > KEEP_SECONDS:
            queue.popleft()

    async def updates(self, key: str, offset: int, wait: float) -> list[dict[str, Any]]:
        """Сообщения для Notio после `offset`; если их нет — ждёт до `wait` секунд. Забранные сообщения уходят из очереди."""
        self.seen[key] = self.clock()
        queue = self.queues.setdefault(key, deque())
        while queue and queue[0]["update_id"] < offset:
            queue.popleft()
        self._drop_old(queue)
        if not queue and wait > 0:
            event = self.events.setdefault(key, asyncio.Event())
            event.clear()
            try:
                await asyncio.wait_for(event.wait(), timeout=wait)
            except asyncio.TimeoutError:
                pass
            self.seen[key] = self.clock()
        return [{k: v for k, v in item.items() if k != "at"} for item in queue if item["update_id"] >= offset]

    async def may_send(self, key: str, chat_id: int) -> bool:
        """Notio может писать только в чат, привязанный к нему самому."""
        return (await self._data())["links"].get(str(chat_id)) == key


def _chunks(text: str) -> list[str]:
    text = text or "…"
    return [text[i:i + MESSAGE_CHARS] for i in range(0, len(text), MESSAGE_CHARS)]


def make_app(relay: NotioRelay, send: Callable[[int, str], Awaitable[None]], bot_name: Callable[[], Awaitable[str]]) -> web.Application:
    """HTTP для Notio. Заголовок `Authorization: Notio <код>`; незнакомый код — 401."""

    async def instance(request: web.Request) -> str:
        header = request.headers.get("Authorization", "")
        code = header[6:] if header.startswith("Notio ") else ""
        key = await relay.by_code(code) if code else None
        if key is None:
            raise web.HTTPUnauthorized(text='{"error":"unknown code"}', content_type="application/json")
        return key

    async def hello(request: web.Request) -> web.Response:
        key = await instance(request)
        relay.seen[key] = relay.clock()
        name = (await relay.instances())[key]["name"]
        return web.json_response({"ok": True, "bot": await bot_name(), "name": name})

    async def updates(request: web.Request) -> web.Response:
        key = await instance(request)
        try:
            offset = int(request.query.get("offset", "0"))
            wait = min(max(float(request.query.get("wait", "0")), 0.0), 55.0)
        except ValueError:
            raise web.HTTPBadRequest(text='{"error":"bad query"}', content_type="application/json")
        return web.json_response({"ok": True, "updates": await relay.updates(key, offset, wait)})

    async def send_message(request: web.Request) -> web.Response:
        key = await instance(request)
        try:
            body = await request.json()
            chat_id = int(body["chat_id"])
            text = str(body["text"])
        except (ValueError, KeyError, TypeError):
            raise web.HTTPBadRequest(text='{"error":"bad body"}', content_type="application/json")
        if not await relay.may_send(key, chat_id):
            raise web.HTTPForbidden(text='{"error":"chat is not bound to this Notio"}', content_type="application/json")
        for piece in _chunks(text):
            await send(chat_id, piece)
        return web.json_response({"ok": True})

    app = web.Application(client_max_size=256 * 1024)
    app.router.add_get("/notio/v1/hello", hello)
    app.router.add_get("/notio/v1/updates", updates)
    app.router.add_post("/notio/v1/send", send_message)
    return app


HELP = (
    "Notio — заметки на вашем компьютере.\n"
    "/notio КОД — подключиться к Notio (код из 12 символов показывает Notio; сообщение с кодом я удалю).\n"
    "/n поручение — отправить поручение в подключённый Notio, например: /n какие заметки в папке Работа?\n"
    "/n_undo — откатить последнее изменение, /n_yes — подтвердить, /notio_off — отключиться.\n"
    "Notio ответит, когда его владелец разрешит вам доступ в самом Notio."
)


def register_notio_relay(router: Router, store_of: Callable[[], Any], is_owner: Callable[[int | None], Awaitable[bool]]) -> NotioRelay:
    """Команды и админка Notio. Регистрировать до общего обработчика текста. Вернёт ретранслятор для HTTP-сервера."""
    relay = NotioRelay(_LazyStore(store_of))
    waiting_code: set[int] = set()

    def private(message: Message) -> bool:
        return message.chat.type == "private" and message.from_user is not None

    def who(message: Message) -> str:
        user = message.from_user
        name = " ".join(p for p in (user.first_name, user.last_name) if p)
        return (name + (f" @{user.username}" if user.username else "")).strip()

    async def deliver(message: Message, key: str, text: str) -> None:
        relay.forward(key, message.chat.id, message.from_user.id, who(message), text)
        if not relay.online(key):
            await message.answer("Notio сейчас не на связи. Поручение подождёт 10 минут: если Notio подключится, он его получит.")

    @router.message(Command("notio"), F.chat.type == "private")
    async def notio_command(message: Message, command: CommandObject) -> None:
        if not private(message):
            return
        args = (command.args or "").strip()
        if not args:
            key = await relay.linked(message.chat.id)
            name = (await relay.instances()).get(key, {}).get("name") if key else None
            await message.answer(HELP + (f"\n\nСейчас подключено: Notio «{name}»." if name else "\n\nСейчас ничего не подключено."))
            return
        code, rest = split_code(args)
        # Сообщение с кодом не остаётся в чате.
        try:
            await message.delete()
        except Exception:  # noqa: BLE001 - удалить не всегда можно; код всё равно проверяется
            pass
        key = await relay.link(message.chat.id, message.from_user.id, code) if code else None
        if key is None:
            await message.answer(wrong_code_words(args.split()[0]) if code is None else "Код не подошёл. Проверьте его в Notio (12 символов) и что владелец бота ввёл его в /admin → Notio.")
            return
        name = (await relay.instances())[key]["name"]
        await message.answer(f"Подключено: Notio «{name}». Пишите /n поручение. Если Notio не отвечает — владелец Notio должен разрешить вас в самом Notio.")
        if rest:
            await deliver(message, key, rest)
        else:
            # Notio узнаёт о человеке сразу и показывает его в списке «Просят доступ».
            relay.forward(key, message.chat.id, message.from_user.id, who(message), "/start")

    async def to_linked(message: Message, text: str) -> None:
        key = await relay.linked(message.chat.id)
        if key is None:
            await message.answer("Сначала подключитесь к Notio: /notio КОД. Код показывает Notio: Настройки → Помощник → Telegram-бот.")
            return
        await deliver(message, key, text)

    @router.message(Command("n"), F.chat.type == "private")
    async def n_command(message: Message, command: CommandObject) -> None:
        text = (command.args or "").strip()
        if not text:
            await message.answer("Напишите поручение после /n, например: /n добавь в список Покупки молоко")
            return
        await to_linked(message, text)

    @router.message(Command("n_undo"), F.chat.type == "private")
    async def n_undo(message: Message) -> None:
        await to_linked(message, "/undo")

    @router.message(Command("n_yes"), F.chat.type == "private")
    async def n_yes(message: Message) -> None:
        await to_linked(message, "/yes")

    @router.message(Command("notio_off"), F.chat.type == "private")
    async def notio_off(message: Message) -> None:
        await message.answer("Отключено от Notio." if await relay.unlink(message.chat.id) else "Этот чат не был подключён к Notio.")

    # ---- админка владельца бота
    async def admin_view() -> tuple[str, InlineKeyboardMarkup]:
        items = await relay.instances()
        lines = ["Notio, подключённые к боту:"]
        rows = [[InlineKeyboardButton(text="➕ Ввести код Notio", callback_data="notio:add")]]
        if not items:
            lines.append("пока ни одного. Нажмите «Ввести код Notio» и отправьте код, который показывает Notio.")
        for key, item in items.items():
            state = "на связи" if relay.online(key) else "не на связи"
            lines.append(f"• {item['name']} — {state}")
            rows.append([InlineKeyboardButton(text=f"🗑 Убрать «{item['name']}»", callback_data=f"notio:del:{key}")])
        rows.append([InlineKeyboardButton(text="↩️ В админку", callback_data="admin")])
        return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)

    @router.callback_query(F.data == "notio:home")
    async def notio_home(callback: CallbackQuery) -> None:
        if not await is_owner(callback.from_user.id):
            await callback.answer("Только для владельца.", show_alert=True)
            return
        text, keyboard = await admin_view()
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    @router.callback_query(F.data == "notio:add")
    async def notio_add_button(callback: CallbackQuery) -> None:
        if not await is_owner(callback.from_user.id):
            await callback.answer("Только для владельца.", show_alert=True)
            return
        waiting_code.add(callback.from_user.id)
        await callback.message.answer("Отправьте код Notio (12 символов). Можно добавить имя через пробел: ABCD-EFGH-JKMN Дом. /cancel — отмена.")
        await callback.answer()

    @router.callback_query(F.data.startswith("notio:del:"))
    async def notio_delete(callback: CallbackQuery) -> None:
        if not await is_owner(callback.from_user.id):
            await callback.answer("Только для владельца.", show_alert=True)
            return
        name = await relay.remove(callback.data.removeprefix("notio:del:"))
        await callback.answer(f"Notio «{name}» убран." if name else "Уже убран.")
        text, keyboard = await admin_view()
        await callback.message.edit_text(text, reply_markup=keyboard)

    async def add_from(message: Message, args: str) -> None:
        code, name = split_code(args)
        try:
            await message.delete()
        except Exception:  # noqa: BLE001
            pass
        ok, text = await relay.add(code or args, name)
        await message.answer(text)

    @router.message(Command("notio_add"), F.chat.type == "private")
    async def notio_add_command(message: Message, command: CommandObject) -> None:
        if not await is_owner(message.from_user.id if message.from_user else None):
            return
        await add_from(message, (command.args or "").strip())

    async def waits_code(message: Message) -> bool:
        return message.chat.type == "private" and message.from_user is not None and message.from_user.id in waiting_code

    @router.message(F.text, waits_code)
    async def notio_code_typed(message: Message) -> None:
        waiting_code.discard(message.from_user.id)
        if (message.text or "").strip().lower() in ("/cancel", "отмена"):
            await message.answer("Отменено.")
            return
        if await is_owner(message.from_user.id):
            await add_from(message, message.text or "")

    return relay


class _LazyStore:
    """Хранилище создаётся в main() позже регистрации обработчиков: берём его в момент обращения."""

    def __init__(self, store_of: Callable[[], Any]) -> None:
        self.store_of = store_of

    async def get(self, key: str) -> Any:
        return await self.store_of().get(key)

    async def set(self, key: str, value: Any) -> None:
        await self.store_of().set(key, value)


async def start_relay_server(relay: NotioRelay, send: Callable[[int, str], Awaitable[None]], bot_name: Callable[[], Awaitable[str]]) -> web.AppRunner:
    """Запускает HTTP для Notio на `NOTIO_RELAY_HOST:NOTIO_RELAY_PORT` (по умолчанию 127.0.0.1:8790)."""
    host = os.getenv("NOTIO_RELAY_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("NOTIO_RELAY_PORT", "8790"))
    runner = web.AppRunner(make_app(relay, send, bot_name), access_log=None)
    await runner.setup()
    await web.TCPSite(runner, host, port).start()
    log.info("Notio relay listens on %s:%s", host, port)
    return runner

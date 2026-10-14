"""Связь с Notio: коды, привязка чатов, очередь поручений и HTTP для Notio (bot/notio_relay.py)."""
import asyncio
import unittest

from aiohttp.test_utils import TestClient, TestServer

from bot.notio_relay import NotioRelay, code_hash, make_app, normalize_code, split_code
from tests.support import Store

CODE = "ABCD-EFGH-JKMN"
OTHER = "2345-6789-ABCD"


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class CodeTests(unittest.TestCase):
    def test_a_code_is_read_as_notio_makes_it(self):
        self.assertEqual("ABCDEFGHJKMN", normalize_code("abcd efgh-jkmn"))
        self.assertEqual("0113", normalize_code("OIL3"))
        self.assertEqual(code_hash("abcd-efgh-jkmn"), code_hash("ABCDEFGHJKMN"))

    def test_a_code_is_split_from_the_request(self):
        self.assertEqual(("ABCDEFGHJKMN", "какие заметки?"), split_code("ABCD-EFGH-JKMN какие заметки?"))
        self.assertEqual(("ABCDEFGHJKMN", "привет"), split_code("ABCD EFGH JKMN привет"))
        self.assertEqual((None, "какие заметки в папке"), split_code("какие заметки в папке"))
        self.assertEqual((None, "ABCD"), split_code("ABCD"))


class RelayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.clock = Clock()
        self.relay = NotioRelay(Store(), self.clock)

    async def test_only_a_code_the_owner_entered_binds_a_chat(self):
        ok, _ = await self.relay.add("short")
        self.assertFalse(ok)
        ok, _ = await self.relay.add(CODE, "Дом")
        self.assertTrue(ok)
        ok, text = await self.relay.add(CODE.lower(), "Ещё раз")
        self.assertFalse(ok)
        self.assertIn("Дом", text)
        # Бот хранит только хэш кода.
        self.assertNotIn("ABCDEFGHJKMN", str(self.relay.store.data))

        self.assertIsNone(await self.relay.link(42, 42, OTHER))
        key = await self.relay.link(42, 42, CODE)
        self.assertIsNotNone(key)
        self.assertEqual(key, await self.relay.linked(42))
        self.assertTrue(await self.relay.may_send(key, 42))
        self.assertFalse(await self.relay.may_send(key, 77))
        self.assertTrue(await self.relay.unlink(42))
        self.assertIsNone(await self.relay.linked(42))

    async def test_wrong_codes_stop_being_checked_for_an_hour(self):
        await self.relay.add(CODE, "Дом")
        for _ in range(5):
            self.assertIsNone(await self.relay.link(77, 77, OTHER))
        self.assertIsNone(await self.relay.link(77, 77, CODE))
        self.clock.now += 3601
        self.assertIsNotNone(await self.relay.link(77, 77, CODE))

    async def test_a_removed_notio_unbinds_its_chats(self):
        await self.relay.add(CODE, "Дом")
        key = await self.relay.link(42, 42, CODE)
        self.assertEqual("Дом", await self.relay.remove(key))
        self.assertIsNone(await self.relay.linked(42))
        self.assertIsNone(await self.relay.by_code(CODE))

    async def test_notio_gets_the_requests_once_and_waits_for_new_ones(self):
        await self.relay.add(CODE, "Дом")
        key = await self.relay.by_code(CODE)
        self.relay.forward(key, 42, 42, "Vic", "первое")
        first = await self.relay.updates(key, 0, 0)
        self.assertEqual(["первое"], [u["text"] for u in first])
        # Ожидание кончается, как только пришло новое сообщение.
        waiting = asyncio.create_task(self.relay.updates(key, first[-1]["update_id"] + 1, 5))
        await asyncio.sleep(0.05)
        self.relay.forward(key, 42, 42, "Vic", "второе")
        second = await asyncio.wait_for(waiting, 2)
        self.assertEqual(["второе"], [u["text"] for u in second])
        self.assertTrue(self.relay.online(key))
        # Старое поручение не копится вечно.
        self.relay.forward(key, 42, 42, "Vic", "старое")
        self.clock.now += 601
        self.assertEqual([], await self.relay.updates(key, second[-1]["update_id"] + 1, 0))
        self.assertFalse(self.relay.online(key) and self.clock.now - self.relay.seen[key] > 120)


class HttpTests(unittest.IsolatedAsyncioTestCase):
    async def test_notio_speaks_to_the_bot_with_its_code(self):
        relay = NotioRelay(Store())
        await relay.add(CODE, "Дом")
        key = await relay.link(42, 42, CODE)
        sent = []

        async def send(chat_id, text):
            sent.append((chat_id, text))

        async def name():
            return "@my_bot"

        client = TestClient(TestServer(make_app(relay, send, name)))
        await client.start_server()
        try:
            self.assertEqual(401, (await client.get("/notio/v1/hello")).status)
            self.assertEqual(401, (await client.get("/notio/v1/hello", headers={"Authorization": "Notio " + OTHER})).status)
            auth = {"Authorization": "Notio " + CODE}
            hello = await (await client.get("/notio/v1/hello", headers=auth)).json()
            self.assertEqual({"ok": True, "bot": "@my_bot", "name": "Дом"}, hello)

            relay.forward(key, 42, 42, "Vic @vic", "какие заметки?")
            body = await (await client.get("/notio/v1/updates?offset=0&wait=0", headers=auth)).json()
            self.assertEqual([{"update_id": 1, "chat_id": 42, "user_id": 42, "name": "Vic @vic", "text": "какие заметки?"}], body["updates"])

            self.assertEqual(200, (await client.post("/notio/v1/send", json={"chat_id": 42, "text": "x" * 4500}, headers=auth)).status)
            self.assertEqual([4000, 500], [len(t) for _, t in sent])
            # В чужой чат Notio писать не может.
            self.assertEqual(403, (await client.post("/notio/v1/send", json={"chat_id": 77, "text": "spam"}, headers=auth)).status)
            self.assertEqual(2, len(sent))
        finally:
            await client.close()


if __name__ == "__main__":
    unittest.main()

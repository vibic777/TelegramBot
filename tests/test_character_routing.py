import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import bot.main as main
from bot.personas import PERSONA_LABELS, team_call_personas, topic_persona
from bot.persona_jokes import PERSONA_JOKE_BANK
from bot.jokes import joke_request


class RoutingTests(unittest.TestCase):
    def test_direct_game_question_uses_animal_specialist(self):
        with patch("bot.main.random.choice", side_effect=lambda options: options[0]) as choice:
            persona = main.request_specialist("Посоветуй игру", None, random_sticker=False,
                                              mood_sticker=False, directly_addressed=True)
        self.assertIn(persona, {"pesel", "cat"})
        self.assertEqual(("pesel", "cat"), choice.call_args.args[0])

    def test_natasha_aliases_in_single_and_joint_addresses(self):
        for alias in ("Наташа", "Ната", "Натусик", "Натаха", "Натка", "Блондинка",
                      "Нате", "Натусику", "Натахе", "Натке", "Блондинке",
                      "Natasha", "Nata", "Natusik", "Nataha", "Natakha", "Natka",
                      "Blonde", "Blond", "Blondinka", "Natashenka", "Natashka"):
            with self.subTest(alias=alias):
                self.assertEqual(main.requested_persona(alias + " с Рождеством"), "natasha")
                self.assertEqual(set(team_call_personas(alias + " и Грут привет")), {"natasha", "groot"})

    def test_collective_addresses(self):
        for text in ("Команда А", "Тима как дела?", "Друзья и подруги ау", "Друзья", "Банда привет", "Тусовка!", "Тима ау", "Team, how are you?"):
            with self.subTest(text=text):
                self.assertEqual(set(team_call_personas(text)), set(PERSONA_LABELS))

    def test_only_named_characters(self):
        for text, expected in (
            ("Ракета и Грут привет", {"rocket", "groot"}),
            ("Настя, Наташа, Мяу расскажите анекдот", {"nastya", "natasha", "cat"}),
            ("Nasty, Natasha, Grut, Stich hello", {"nastya", "natasha", "groot", "stitch"}),
            ("Wow и Meu привет", {"pesel", "cat"}),
        ):
            with self.subTest(text=text): self.assertEqual(set(team_call_personas(text)), expected)

    def test_girlfriends_and_narrative(self):
        self.assertEqual(set(team_call_personas("Подруги ау")), {"nastya", "natasha"})
        self.assertIsNone(team_call_personas("Сегодня обсуждали команду разработчиков"))
        self.assertIsNone(team_call_personas("История про Ракету и Грута"))

    def test_local_collections(self):
        self.assertEqual(set(PERSONA_JOKE_BANK), set(PERSONA_LABELS))
        for persona, entries in PERSONA_JOKE_BANK.items():
            with self.subTest(persona=persona):
                self.assertGreaterEqual(len(entries), 500)
                self.assertEqual(len(entries), len({text for _, text in entries}))
                self.assertTrue(all(len(text) < 1000 and "{topic}" not in text for _, text in entries))

    def test_general_humor_and_specialists(self):
        for text in ("анекдот", "расскажи анекдот", "юмор", "пошути"):
            self.assertEqual(joke_request(text), "general")
        for text, expected in (("психология", "natasha"), ("как поливать растения", "groot"), ("рецепт десерта", "stitch"), ("мясное блюдо", "rocket"), ("корм для собак", "pesel"), ("еда для кошек", "cat")):
            self.assertEqual(topic_persona(text), expected)
        self.assertEqual(main.requested_persona("Nasty юмор"), "nastya")
        self.assertEqual(topic_persona("объясни квадратные уравнения"), "nastya")

    def test_nastya_aliases_are_respectful(self):
        for alias in ("Настя", "Настенька", "Черри", "учительница", "физичка", "математичка", "айтишница"):
            with self.subTest(alias=alias):
                self.assertEqual(main.requested_persona(alias + " привет"), "nastya")
        for insult in ("шлюха", "лохушка", "дура", "тупая", "сучка", "шалава", "овца", "курица", "ботиха", "ламоботина", "училка"):
            with self.subTest(insult=insult):
                self.assertNotEqual(main.requested_persona(insult + " привет"), "nastya")
                self.assertIsNone(team_call_personas(insult + " и Грут привет"))

    def test_nastya_prompt_is_kind_teacher(self):
        from bot.keyboards import NASTYA_ONLY_MODES, mode_label
        from bot.personas import PERSONA_DEFAULT_PROMPTS, PERSONA_TOPIC_PROMPTS
        prompt = PERSONA_DEFAULT_PROMPTS["nastya"]
        self.assertIn("kind and responsive", prompt)
        self.assertIn("physics and mathematics", prompt)
        self.assertIn("IT specialist", prompt)
        self.assertIn("mathematics", PERSONA_TOPIC_PROMPTS["nastya"])
        self.assertEqual(NASTYA_ONLY_MODES["учительница"], "Учительница")
        self.assertNotIn("училка", NASTYA_ONLY_MODES)
        self.assertEqual(mode_label("училка"), "Учительница")
        self.assertIn("mathematics", {category for category, _ in PERSONA_JOKE_BANK["nastya"]})

    def test_direct_bot_address_randomly_selects_one_character(self):
        with patch.object(main.random, "choice", return_value="rocket") as choose:
            self.assertEqual(main.request_specialist(
                "привет", None, random_sticker=False, mood_sticker=False, directly_addressed=True,
            ), "rocket")
            self.assertEqual(tuple(choose.call_args.args[0]), tuple(main.PERSONAS))
            self.assertEqual(main.request_specialist(
                "психология", None, random_sticker=False, mood_sticker=False, directly_addressed=True,
            ), "natasha")
            self.assertEqual(main.request_specialist(
                "юмор", "general", random_sticker=False, mood_sticker=False, directly_addressed=True,
            ), "rocket")
            self.assertEqual(main.request_specialist(
                "картинка", None, random_sticker=True, mood_sticker=False, directly_addressed=True,
            ), "rocket")
            self.assertEqual(main.request_specialist(
                "эмодзи", None, random_sticker=False, mood_sticker=True, directly_addressed=True,
            ), "rocket")
        self.assertEqual(main.request_specialist(
            "психология", None, random_sticker=False, mood_sticker=False, directly_addressed=False,
        ), "natasha")

    def test_history_analysis_request_variants(self):
        for text, expected in (
            ("@example_bot проанализируй 30 последних сообщений и вычисли психологический возраст автора", (True, 30)),
            ("Настя, прочитай последние сообщения и скажи, какие темы меня волнуют", (True, None)),
            ("Проанализируй последние 12 сообщений", (True, 12)),
            ("Analyze the last 25 messages", (True, 25)),
            ("Настя, психологический возраст автора", (False, None)),
        ):
            with self.subTest(text=text):
                self.assertEqual(main.requested_history_analysis(text), expected)


class MemoryStore:
    def __init__(self): self.data = {}
    async def get(self, key): return self.data.get(key)
    async def set(self, key, value): self.data[key] = value


class Message:
    def __init__(self, text, number=100):
        self.text = text
        self.chat = SimpleNamespace(id=1, type="private", title=None)
        self.from_user = SimpleNamespace(id=1, is_bot=False, username="owner", full_name="Owner")
        self.message_id = number
        self.reply_to_message = None
        self.outputs = []
    async def answer(self, text, **kwargs):
        self.outputs.append(text)
        return SimpleNamespace(message_id=self.message_id + len(self.outputs))
    async def reply(self, text, **kwargs): return await self.answer(text, **kwargs)
    async def answer_sticker(self, sticker, **kwargs):
        return await self.answer(str(sticker.path), **kwargs)


class DispatchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.patches = [patch.object(main, "config", SimpleNamespace(owner_id=1), create=True),
                        patch.object(main, "store", MemoryStore(), create=True),
                        patch.object(main, "request_queue", None),
                        patch.object(main, "request_queue_worker", None)]
        for p in self.patches: p.start()
    async def asyncTearDown(self):
        for p in reversed(self.patches): p.stop()

    async def test_generic_sticker_chooses_character_then_its_collection(self):
        for text in ("Стикер", "Картинка!", "sticker", "picture", "image"):
            for persona in PERSONA_LABELS:
                with self.subTest(text=text, persona=persona):
                    selected = main.persona_stickers_for(persona)[-1]
                    msg = Message(text)
                    with patch.object(main.random, "choice", side_effect=[persona, selected]) as choose:
                        await main.process_chat_message(msg, text)
                    self.assertEqual(msg.outputs, [str(selected)])
                    self.assertEqual(tuple(choose.call_args_list[0].args[0]), tuple(main.PERSONAS))
                    self.assertEqual(choose.call_args_list[1].args[0], main.persona_stickers_for(persona))

    async def test_named_sticker_uses_only_requested_collection(self):
        for name, persona in (("Настя", "nastya"), ("Черри", "nastya"), ("Натусик", "natasha"),
                              ("Blonde", "natasha"), ("Гав", "pesel"), ("Meu", "cat"),
                              ("Стич", "stitch"), ("Грут", "groot"), ("Енот Ракета", "rocket")):
            for word in ("стикер", "картинка"):
                with self.subTest(name=name, word=word):
                    msg = Message(name + " " + word)
                    await main.process_chat_message(msg, msg.text)
                    self.assertEqual(len(msg.outputs), 1)
                    self.assertIn(msg.outputs[0], [str(path) for path in main.persona_stickers_for(persona)])

    async def test_sticker_collections_exclude_archives_and_adult_reactions(self):
        for persona in PERSONA_LABELS:
            options = main.persona_stickers_for(persona)
            self.assertTrue(options)
            self.assertTrue(all("imports" not in path.parts and "adult" not in path.name for path in options))
        msg = Message("Команда картинка")
        await main.process_chat_message(msg, msg.text)
        self.assertEqual(len(msg.outputs), 7)

    async def test_unaddressed_holidays_send_all_seven_stickers(self):
        for text in ("Новый год!", "Рождество!", "8 марта!", "23 февраля!", "1 мая!", "9 мая!"):
            with self.subTest(text=text):
                msg = Message(text)
                with patch.object(main.random, "shuffle", side_effect=lambda items: items.reverse()):
                    await main.process_chat_message(msg, text)
                self.assertEqual(len(msg.outputs), 7)
                holiday = main.holiday_sticker_request(text)
                for output, persona in zip(msg.outputs, list(PERSONA_LABELS)[::-1]):
                    self.assertIn(output, [str(path) for path in main.holiday_stickers_for(persona, holiday)])

    async def test_holiday_dispatch_in_allowed_keyword_group(self):
        msg = Message("Новый год!")
        msg.chat = SimpleNamespace(id=-100, type="supergroup", title="Test")
        await main.store.set("allowed_chats", [-100])
        await main.store.set("group_reply_mode", "keywords")
        fake_bot = SimpleNamespace(get_me=AsyncMock(return_value=SimpleNamespace(id=2, username="testbot")))
        with patch.object(main, "bot", fake_bot, create=True):
            await main.process_chat_message(msg, msg.text)
        self.assertEqual(len(msg.outputs), 7)

    async def test_named_holidays_and_aliases(self):
        for text, personas in (("Настя с Новым годом!", ["nastya"]),
                               ("Настя Рождество!", ["nastya"]),
                               ("Настя с Рождеством!", ["nastya"]),
                               ("Черри с Рождеством", ["nastya"]),
                               ("Черри и Грут с Рождеством", ["nastya", "groot"]),
                               ("Наташа с Рождеством", ["natasha"])):
            with self.subTest(text=text):
                msg = Message(text)
                await main.process_chat_message(msg, text)
                self.assertEqual(len(msg.outputs), len(personas))
                holiday = main.holiday_sticker_request(text)
                expected = {str(path) for persona in personas for path in main.holiday_stickers_for(persona, holiday)}
                self.assertTrue(set(msg.outputs) <= expected)

    async def test_team_jokes_without_model_in_shuffled_sequence(self):
        msg = Message("Команда юмор")
        with patch.object(main.random, "shuffle", side_effect=lambda items: items.reverse()):
            await main.process_chat_message(msg, msg.text)
        self.assertEqual(len(msg.outputs), 7)
        expected = list(PERSONA_LABELS)[::-1]
        for output, persona in zip(msg.outputs, expected):
            self.assertTrue(output.startswith(main.persona_speaker_label(persona) + ":"), output)

    async def test_pair_and_single_jokes(self):
        for text, count in (("Ракета и Грут юмор", 2), ("Настя юмор", 1), ("Настя анекдот про видеокарту", 1), ("юмор", 1)):
            msg = Message(text)
            await main.process_chat_message(msg, text)
            self.assertEqual(len(msg.outputs), count, msg.outputs)

    async def test_requests_in_same_chat_do_not_interleave(self):
        order = []
        async def worker(message, text, **kwargs):
            order.append((message.message_id, "start"))
            await asyncio.sleep(0)
            order.append((message.message_id, "end"))
        with patch.object(main, "_process_chat_message", side_effect=worker):
            await asyncio.gather(main.process_chat_message(Message("first", 1), "first"),
                                 main.process_chat_message(Message("second", 2), "second"))
        self.assertEqual(order, [(1, "start"), (1, "end"), (2, "start"), (2, "end")])


if __name__ == "__main__":
    unittest.main()

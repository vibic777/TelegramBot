import unittest

from bot.user_memory import context, enabled, parse_facts, remember, memory_request, own_memory_text, sanitize_facts, load_memories
from bot.hardware import hardware_request
from bot.user_memory import explicit_user_gender, remember_user_profile, GENDER_FACTS, GENDER_GUESSES, stated_user_age, format_memory_facts
from datetime import date
from unittest.mock import patch
from bot.user_memory import parse_memory_update, save_memories
from bot.memory_admin import memory_pages, register_memory_admin
from types import SimpleNamespace


from tests.support import Store, run_immediate


class MemoryTests(unittest.TestCase):
    def test_admin_memory_filters_and_pagination(self):
        memories = {"natasha:1": ["Наташа об одном"], "natasha:2": ["Наташа о втором"],
                    "nastya:1": ["Настя об одном"]}
        pair = "\n".join(memory_pages(memories, {}, persona="natasha", user_id=1))
        self.assertIn("Наташа об одном", pair)
        self.assertNotIn("Наташа о втором", pair)
        self.assertNotIn("Настя об одном", pair)
        character = "\n".join(memory_pages(memories, {}, persona="natasha"))
        self.assertIn("Наташа о втором", character)
        self.assertNotIn("Настя об одном", character)
        user = "\n".join(memory_pages(memories, {}, user_id=1))
        self.assertIn("Настя об одном", user)
        self.assertNotIn("Наташа о втором", user)
        large = {"natasha:1": [str(i) + "x" * 240 for i in range(30)]}
        pages = memory_pages(large, {})
        self.assertGreater(len(pages), 1)
        self.assertTrue(all(len(page) <= 3400 for page in pages))
        self.assertTrue(all("пользователь ID 1" in page for page in pages))
        self.assertIn("пока нет", memory_pages({}, {})[0])

    def test_admin_memory_view_rejects_non_owner_before_reading(self):
        handlers = []

        class Router:
            def callback_query(self, filter):
                def register(handler):
                    handlers.append(handler)
                    return handler
                return register

        async def not_owner(uid):
            return False

        class Callback:
            from_user = SimpleNamespace(id=99)
            data = "pm:view:all:all:0"
            denied = False

            async def answer(self, text, **kwargs):
                self.denied = kwargs.get("show_alert", False)

        def forbidden_store():
            raise AssertionError("Unauthorised read")

        register_memory_admin(Router(), forbidden_store, not_owner, lambda: 1)
        callback = Callback()
        run_immediate(handlers[0](callback))
        self.assertTrue(callback.denied)

    def test_fact_dates_only_refresh_when_reconfirmed_and_clear_with_facts(self):
        store = Store({"personal_memory_fact_dates": {"natasha:1": {"Любит чай": "2025-01-01"}}})
        with patch("bot.user_memory.memory_today", return_value=date(2026, 10, 10)):
            run_immediate(save_memories(store, {"natasha:1": ["Любит чай", "Работает инженером"]}))
            self.assertEqual("2025-01-01", store.data["personal_memory_fact_dates"]["natasha:1"]["Любит чай"])
            self.assertEqual("2026-10-10", store.data["personal_memory_fact_dates"]["natasha:1"]["Работает инженером"])
            run_immediate(save_memories(store, {"natasha:1": ["Любит чай"]}, renewed={"natasha:1": {"Любит чай"}}))
            self.assertEqual({"Любит чай": "2026-10-10"}, store.data["personal_memory_fact_dates"]["natasha:1"])
            run_immediate(save_memories(store, {}))
            self.assertEqual({}, store.data["personal_memory_fact_dates"])

    def test_current_evidence_is_required_to_refresh_existing_fact(self):
        facts, touched = parse_memory_update('[{"fact":"Любит чай","evidence":"люблю чай"},{"fact":"Инженер","evidence":""}]', "Я люблю чай")
        self.assertEqual(["Любит чай", "Инженер"], facts)
        self.assertEqual({"Любит чай"}, touched)
        _, touched = parse_memory_update('[{"fact":"Любит чай","evidence":"выдуманная цитата"}]', "Привет")
        self.assertEqual(set(), touched)

    def test_age_without_years_replaces_value_and_refreshes_timestamp(self):
        store = Store({"personal_memory_personas": {"natasha": True}, "personal_memory_users": {"1": True}})
        with patch("bot.user_memory.memory_today", return_value=date(2025, 1, 1)):
            run_immediate(remember_user_profile(store, "natasha", 1, "Мне 45 лет"))
        with patch("bot.user_memory.memory_today", return_value=date(2026, 10, 10)):
            run_immediate(remember_user_profile(store, "natasha", 1, "Нет, мне 16"))
        facts = store.data["personal_memories"]["natasha:1"]
        self.assertEqual(["Возраст — указан пользователем: 16 лет (на 2026-10-10)."], facts)
        self.assertIn(": 17 лет", format_memory_facts(facts, date(2027, 10, 10))[0])

    def test_tentative_gender_never_overrides_confirmed(self):
        store = Store({"personal_memory_personas": {"natasha": True}, "personal_memory_users": {"1": True}})
        run_immediate(remember_user_profile(store, "natasha", 1, "Я писал вчера"))
        self.assertIn(GENDER_GUESSES["male"], store.data["personal_memories"]["natasha:1"])
        run_immediate(remember_user_profile(store, "natasha", 1, "Я женщина"))
        run_immediate(remember_user_profile(store, "natasha", 1, "Я писал вчера"))
        self.assertEqual([GENDER_FACTS["female"]], store.data["personal_memories"]["natasha:1"])

    def test_age_keeps_timestamp_and_counts_full_years(self):
        fact = stated_user_age("Мне 45 лет", date(2026, 10, 10))
        self.assertIn("указан пользователем", fact)
        self.assertIn("2026-10-10", fact)
        self.assertIn(": 45 лет", format_memory_facts([fact], date(2027, 10, 9))[0])
        self.assertIn(": 46 лет", format_memory_facts([fact], date(2027, 10, 10))[0])
        self.assertIn(": 47 лет", format_memory_facts([fact], date(2028, 10, 10))[0])
        self.assertIn(": 45 лет", format_memory_facts([fact], date(2025, 10, 10))[0])
        guessed = stated_user_age("Мне около 45 лет", date(2026, 10, 10))
        self.assertIn("предположительно: 46 лет", format_memory_facts([guessed], date(2027, 10, 10))[0])
        for text in ("Ему 45 лет", "Психологический возраст 45 лет", 'Он сказал "мне 45 лет"', "Мне 45 лет будет"):
            self.assertIsNone(stated_user_age(text))

    def test_age_correction_overrides_estimate_and_survives_extraction(self):
        store = Store({"personal_memory_personas": {"natasha": True}, "personal_memory_users": {"1": True}})
        run_immediate(remember_user_profile(store, "natasha", 1, "Мне около 30 лет"))
        run_immediate(remember_user_profile(store, "natasha", 1, "Мне 45 лет"))
        run_immediate(remember_user_profile(store, "natasha", 1, "Мне около 50 лет"))

        class LM:
            async def chat(self, model, messages):
                return '["Возраст — указан пользователем: 99 лет."]'

        run_immediate(remember(store, LM(), "model", "natasha", 1, "Привет"))
        self.assertEqual(1, len(store.data["personal_memories"]["natasha:1"]))
        self.assertIn("45 лет", store.data["personal_memories"]["natasha:1"][0])
    def test_gender_requires_direct_self_report(self):
        for text in ("Я мужчина", "Наташа, я мужчина, обращайся ко мне правильно", "Я он", "Обращайся ко мне в мужском роде"):
            self.assertEqual("male", explicit_user_gender(text), text)
        self.assertEqual("female", explicit_user_gender("Я женщина"))
        for text in ("Он мужчина", "Мой друг мужчина", "Наташа женщина", "Я не мужчина", 'Он сказал: "Я мужчина"', "Я писал вчера"):
            self.assertIsNone(explicit_user_gender(text), text)

    def test_gender_correction_overrides_old_context_and_is_retained(self):
        store = Store({"personal_memory_personas": {"natasha": True}, "personal_memory_users": {"1": True},
                       "personal_memories": {"natasha:1": [GENDER_FACTS["female"], "Любит чай"]}})
        run_immediate(remember_user_profile(store, "natasha", 1, "Я мужчина"))
        self.assertNotIn(GENDER_FACTS["female"], store.data["personal_memories"]["natasha:1"])
        self.assertIn(GENDER_FACTS["male"], run_immediate(context(store, "natasha", 1)))

        class LM:
            async def chat(self, model, messages):
                return '["Пользователь — женщина", "Любит чай"]'

        run_immediate(remember(store, LM(), "model", "natasha", 1, "Люблю чай"))
        self.assertEqual([GENDER_FACTS["male"], "Любит чай"], store.data["personal_memories"]["natasha:1"])

    def test_disabled_memory_does_not_persist_gender(self):
        store = Store()
        instruction = run_immediate(remember_user_profile(store, "natasha", 1, "Я мужчина"))
        self.assertIn("мужской род", instruction)
        self.assertEqual({}, store.data)

    def test_old_incorrect_name_is_removed_from_storage_and_context(self):
        store = Store({"personal_memories": {"natasha:1": ["Имя пользователя — Наташа", "Любит анализировать данные"]},
                       "personal_memory_personas": {"natasha": True}, "personal_memory_users": {"1": True}})
        text = run_immediate(own_memory_text(store, 1, "natasha", user_name="FromTheAshes"))
        self.assertNotIn("Имя пользователя", text)
        self.assertIn("FromTheAshes", text)
        self.assertEqual(["Любит анализировать данные"], store.data["personal_memories"]["natasha:1"])
        self.assertNotIn("Имя пользователя", run_immediate(context(store, "natasha", 1)))
        self.assertEqual(1, store.data["personal_memory_revision"])
        run_immediate(load_memories(store))
        self.assertEqual(1, store.data["personal_memory_revision"])

    def test_extraction_separates_character_from_sender_and_filters_names(self):
        store = Store({"personal_memory_personas": {"natasha": True}, "personal_memory_users": {"1": True}})

        class LM:
            async def chat(self, model, messages):
                payload = __import__('json').loads(messages[1]["content"])
                self_payload = payload["sender"]
                assert self_payload["display_name"] == "FromTheAshes"
                assert payload["bot_character"]["name"] == "Наташа"
                return '["Имя пользователя — Наташа", "Любит чай"]'

        run_immediate(remember(store, LM(), "model", "natasha", 1, "Наташа, люблю чай", user_name="FromTheAshes"))
        self.assertEqual(["Любит чай"], store.data["personal_memories"]["natasha:1"])
        self.assertEqual(["Друг пользователя — Наташа"], sanitize_facts([
            "Пользователя зовут Наташа", "User name is Natasha", "Друг пользователя — Наташа"]))

    def test_self_memory_request_aliases(self):
        for text in ("Наташа память", "Наташа память обо мне", "Наташа /memory", "Natasha /memory"):
            self.assertEqual((True, "natasha"), memory_request(text))
        for text in ("/memory", "/memory@example_bot", "@example_bot /memory"):
            self.assertEqual((True, None), memory_request(text))
        for text in ("/memory 123", "Наташа память о другом", "что такое память"):
            self.assertFalse(memory_request(text)[0])

    def test_self_memory_view_isolation_and_disabled_records(self):
        store = Store({"personal_memories": {"natasha:1": ["Свой факт"],
                       "nastya:1": ["Другой персонаж"], "natasha:2": ["Чужой факт"]}})
        text = run_immediate(own_memory_text(store, 1, "natasha"))
        self.assertIn("Свой факт", text)
        self.assertIn("выключена", text)
        self.assertNotIn("Другой персонаж", text)
        self.assertNotIn("Чужой факт", text)
        all_text = run_immediate(own_memory_text(store, 1))
        self.assertIn("Другой персонаж", all_text)
        self.assertNotIn("Чужой факт", all_text)

    def test_memory_heading_uses_actual_sender_name(self):
        text = run_immediate(own_memory_text(Store(), 42, "natasha", user_name="Иван", username="ivan"))
        self.assertIn("Наташа — память о пользователе: Иван (@ivan)", text)
        self.assertIn("Записей пока нет", text)

    def test_ram_aliases_do_not_open_personal_memory(self):
        for text in ("память", "оперативная память", "RAM", "озу", "Наташа оперативная память"):
            self.assertFalse(memory_request(text)[0], text)
            self.assertEqual("ram", hardware_request(text), text)
        self.assertEqual((True, None), memory_request("память обо мне"))

    def test_defaults_and_both_switches(self):
        store = Store()
        self.assertFalse(run_immediate(enabled(store, "nastya", 1)))
        store.data["personal_memory_personas"] = {"nastya": True}
        self.assertFalse(run_immediate(enabled(store, "nastya", 1)))
        store.data["personal_memory_users"] = {"1": True}
        self.assertTrue(run_immediate(enabled(store, "nastya", 1)))
        self.assertFalse(run_immediate(enabled(store, "cat", 1)))
        self.assertFalse(run_immediate(enabled(store, "nastya", 2)))

    def test_isolated_context(self):
        store = Store({"personal_memory_personas": {"nastya": True, "cat": True},
                       "personal_memory_users": {"1": True, "2": True},
                       "personal_memories": {"nastya:1": ["Любит чай"]}})
        self.assertIn("Любит чай", run_immediate(context(store, "nastya", 1)))
        self.assertEqual("", run_immediate(context(store, "cat", 1)))
        self.assertEqual("", run_immediate(context(store, "nastya", 2)))

    def test_extraction_validation(self):
        self.assertEqual(["Факт"], parse_facts('```json\n["Факт", "Факт", ""]\n```'))
        for invalid in ('{"facts": []}', '[1]', 'plain text'):
            with self.assertRaises(ValueError):
                parse_facts(invalid)
        self.assertEqual(30, len(parse_facts(__import__('json').dumps([str(i) for i in range(50)]))))

    def test_clear_during_extraction_does_not_restore_memory(self):
        store = Store({"personal_memory_personas": {"nastya": True},
                       "personal_memory_users": {"1": True}})

        class LM:
            async def chat(self, model, messages):
                store.data["personal_memory_revision"] = 1
                return '["Любит чай"]'

        run_immediate(remember(store, LM(), "model", "nastya", 1, "Люблю чай"))
        self.assertNotIn("nastya:1", store.data.get("personal_memories", {}))

    def test_update_and_disabled_no_model_call(self):
        store = Store({"personal_memory_personas": {"nastya": True},
                       "personal_memory_users": {"1": True}})

        class LM:
            calls = 0

            async def chat(self, model, messages):
                self.calls += 1
                return '["Любит чай"]'

        lm = LM()
        run_immediate(remember(store, lm, "model", "nastya", 1, "Люблю чай"))
        self.assertEqual(["Любит чай"], store.data["personal_memories"]["nastya:1"])
        run_immediate(remember(store, lm, "model", "cat", 1, "Люблю чай"))
        self.assertEqual(1, lm.calls)

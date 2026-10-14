import json
import unittest
from uuid import uuid4
from pathlib import Path
from unittest.mock import patch

from bot.state import StateStore
from tests.support import run_immediate


class StateTests(unittest.TestCase):
    def setUp(self):
        directory = Path.cwd() / "data" / ("state-test-" + uuid4().hex)
        directory.mkdir(parents=True)
        self.path = directory / "state.json"
        self.addCleanup(self.cleanup_files)
        self.store = StateStore(self.path, "обычный", "keywords")

    def cleanup_files(self):
        directory = self.path.parent.resolve()
        self.assertEqual((Path.cwd() / "data").resolve(), directory.parent)
        for path in directory.iterdir():
            path.unlink()
        directory.rmdir()

    def test_updates_persist_together_and_reads_are_isolated(self):
        run_immediate(self.store.update_many({"personal_memories": {"natasha:1": ["Факт"]},
                                             "personal_memory_fact_dates": {"natasha:1": {"Факт": "2026-10-10"}}}))
        loaded = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(["Факт"], loaded["personal_memories"]["natasha:1"])
        returned = run_immediate(self.store.get("personal_memories"))
        returned["natasha:1"].append("Лишнее")
        self.assertEqual(["Факт"], run_immediate(self.store.get("personal_memories"))["natasha:1"])

    def test_failed_replace_preserves_disk_and_rolls_back_memory(self):
        run_immediate(self.store.set("mode", "обычный"))
        original = self.path.read_bytes()
        with patch("bot.state.os.replace", side_effect=OSError("Write failure")):
            with self.assertRaises(OSError):
                run_immediate(self.store.set("mode", "игривый"))
        self.assertEqual(original, self.path.read_bytes())
        self.assertEqual("обычный", run_immediate(self.store.get("mode")))
        self.assertEqual([], list(self.path.parent.glob("*.tmp")))

    def test_corrupt_state_is_not_silently_overwritten(self):
        self.path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(ValueError):
            run_immediate(self.store.load())
        self.assertEqual("{broken", self.path.read_text(encoding="utf-8"))

    def test_history_reads_do_not_mutate_store(self):
        history = [{"role": "user", "content": "Привет"}]
        run_immediate(self.store.set_history("1:2:cat", history))
        history[0]["content"] = "Ошибка"
        returned = run_immediate(self.store.get_history("1:2:cat"))
        returned[0]["content"] = "Ошибка"
        self.assertEqual("Привет", run_immediate(self.store.get_history("1:2:cat"))[0]["content"])

import unittest

from bot.character_context import context_window, set_context_window, window_messages
from tests.support import Store, run_immediate


class ContextTests(unittest.TestCase):
    def test_default_and_independent_settings(self):
        store = Store()
        self.assertEqual(5, run_immediate(context_window(store, "nastya")))
        run_immediate(set_context_window(store, "nastya", 65535))
        self.assertEqual(65535, run_immediate(context_window(store, "nastya")))
        self.assertEqual(5, run_immediate(context_window(store, "cat")))

    def test_zero_and_trimming_are_persona_specific(self):
        store = Store({"history": {"1:2:nastya": [1, 2, 3], "1:2": [1, 2], "1:2:cat": [4, 5]}})
        run_immediate(set_context_window(store, "nastya", 0))
        self.assertEqual([], store.data["history"]["1:2:nastya"])
        self.assertEqual([], store.data["history"]["1:2"])
        self.assertEqual([4, 5], store.data["history"]["1:2:cat"])
        self.assertEqual([], window_messages([1, 2], 0))
        self.assertEqual([2], window_messages([1, 2], 1))

    def test_invalid_limit_does_not_change_state(self):
        store = Store()
        for limit in (-1, 65536):
            with self.assertRaises(ValueError):
                run_immediate(set_context_window(store, "cat", limit))
        self.assertEqual({}, store.data)

import unittest

from bot.continuation import continuation_request, continuation_source, last_speaker


class ContinuationTests(unittest.TestCase):
    def test_russian_and_english_short_followups(self):
        for phrase in ("ещё", "хочу еще", "давай ещё", "ещё фразу", "more", "I want more", "one more", "another one", "continue", "go on"):
            self.assertEqual((True, None), continuation_request(phrase), phrase)
        self.assertEqual((True, "natasha"), continuation_request("Наташа, ещё"))
        self.assertEqual((True, "natasha"), continuation_request("Natasha more"))
        for phrase in ("ещё не готов", "хочу ещё поспать", "more memory", "что ещё умеешь?"):
            self.assertFalse(continuation_request(phrase)[0], phrase)

    def test_persona_window_and_repeated_followups(self):
        events = [{"role": "user", "persona": "natasha", "text": "Напиши стих"},
                  {"role": "assistant", "persona": "natasha", "text": "Первый стих"},
                  {"role": "user", "persona": "cat", "text": "Привет"},
                  {"role": "assistant", "persona": "cat", "text": "Мяу"}]
        self.assertEqual("cat", last_speaker(events))
        self.assertEqual(("Напиши стих", "Первый стих"), continuation_source(events, "natasha", 5))
        self.assertIsNone(continuation_source(events, "natasha", 0))
        self.assertIsNone(continuation_source(events, "natasha", 1))
        events.extend([{"role": "user", "persona": "natasha", "text": "Ещё", "continuation_request": "Напиши стих"},
                       {"role": "assistant", "persona": "natasha", "text": "Другой стих"}])
        self.assertEqual(("Напиши стих", "Другой стих"), continuation_source(events, "natasha", 2))

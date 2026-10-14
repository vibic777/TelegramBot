# Telegram Bot with Local LM Studio

[Русский](README.md) · **English**

**License:** [PolyForm Noncommercial 1.0.0](LICENSE). Noncommercial use is allowed. Commercial use requires a separate agreement with vibic777.


Interesting ideas, and already a useful tool: the bot runs on a local model. For now it is mostly play. Useful features are still ahead, including an integration with the other project, Notio.

A Telegram bot that sends requests to an OpenAI-compatible API served by LM Studio on your own computer. It supports seven configurable characters, private and group chats, per-chat conversation history, owner controls, stickers, and news headlines. Nastya is a kind, responsive physics and mathematics teacher and an IT specialist. Her tone stays respectful and family-friendly in every mode, without flirting, intimate hints, profanity, insults, or demeaning nicknames.

You need Python, a Telegram bot token, and a running LM Studio server. Copy .env.example to .env, configure the local model endpoint and bot settings, install dependencies, then run:

    python -m pip install -r requirements.txt
    python -m bot

Keep the real .env and local bot state private. See the [Russian README](README.md) for detailed setup and commands. Additional project documentation is currently in Russian.

import asyncio
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, path: Path, default_mode: str, default_group_reply_mode: str) -> None:
        self.path = path
        self.data: dict[str, Any] = {
            "model": "",
            "mode": default_mode,
            "group_reply_mode": default_group_reply_mode,
            "history": {},
            "conversation_memory_limit": 50,
            "analysis_memory_limit": 100,
            "request_queue_limit": 50,
            "dialogue_events": {},
            "analysis_messages": {},
            "personal_memory_personas": {},
            "personal_memory_users": {},
            "personal_memories": {},
            "personal_memory_fact_dates": {},
            "personal_memory_revision": 0,
            "character_context_windows": {},
        }
        self.lock = asyncio.Lock()

    async def load(self) -> None:
        async with self.lock:
            if self.path.exists():
                try:
                    stored = json.loads(self.path.read_text(encoding="utf-8"))
                    if isinstance(stored, dict):
                        self.data.update(stored)
                    else:
                        raise ValueError("Файл состояния должен содержать JSON-объект.")
                except (OSError, json.JSONDecodeError) as exc:
                    raise ValueError("Не удалось прочитать data/state.json. Проверьте файл состояния перед запуском; он не будет перезаписан.") from exc

    async def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix=self.path.name + ".", suffix=".tmp", delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(self.data, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    async def get(self, key: str) -> Any:
        async with self.lock:
            return deepcopy(self.data.get(key))

    async def set(self, key: str, value: Any) -> None:
        await self.update_many({key: value})

    async def update_many(self, values: dict[str, Any]) -> None:
        async with self.lock:
            await self._update_unlocked(values)

    async def _update_unlocked(self, values: dict[str, Any]) -> None:
        previous = self.data
        self.data = {**self.data, **deepcopy(values)}
        try:
            await self.save()
        except Exception:
            self.data = previous
            raise

    async def get_history(self, key: str) -> list[dict[str, str]]:
        async with self.lock:
            history = self.data.get("history", {}).get(key, [])
            return deepcopy(history)

    async def set_history(self, key: str, history: list[dict[str, str]]) -> None:
        async with self.lock:
            histories = {**self.data.get("history", {}), key: deepcopy(history)}
            await self._update_unlocked({"history": histories})

    async def clear_history(self, key: str) -> None:
        async with self.lock:
            histories = dict(self.data.get("history", {}))
            histories.pop(key, None)
            await self._update_unlocked({"history": histories})

    async def clear_all_history(self) -> None:
        await self.update_many({"history": {}})

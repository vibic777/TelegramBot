"""In-memory test helpers; no Telegram, LM Studio or event-loop IO."""
from copy import deepcopy


class Store:
    def __init__(self, data=None):
        self.data = deepcopy(data or {})

    async def get(self, key):
        return deepcopy(self.data.get(key))

    async def set(self, key, value):
        self.data[key] = deepcopy(value)

    async def update_many(self, values):
        self.data.update(deepcopy(values))


def run_immediate(coro):
    """Execute a coroutine which performs no suspending IO."""
    try:
        coro.send(None)
    except StopIteration as result:
        return result.value
    coro.close()
    raise AssertionError("Unexpected IO suspension")

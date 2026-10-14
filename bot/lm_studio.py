import httpx


class LMStudioClient:
    def __init__(self, base_url: str, api_key: str, timeout: float) -> None:
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    async def list_models(self) -> list[dict[str, str]]:
        response = await self.client.get("/models")
        response.raise_for_status()
        payload = response.json()
        return [
            {"id": str(item["id"]), "owned_by": str(item.get("owned_by", "local"))}
            for item in payload.get("data", [])
            if isinstance(item, dict) and item.get("id")
        ]

    async def chat(self, model: str, messages: list[dict[str, str]]) -> str:
        response = await self.client.post(
            "/chat/completions",
            json={"model": model, "messages": messages, "temperature": 0.9},
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"].strip()

    async def close(self) -> None:
        await self.client.aclose()

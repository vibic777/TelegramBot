from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    owner_id: int
    lm_studio_base_url: str
    lm_studio_api_key: str
    default_model: str
    pesel_system_prompt: str
    default_mode: str
    system_prompt: str
    context_length: int
    group_reply_mode: str
    request_timeout: float
    log_level: str


def load_config() -> Config:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    owner_id = os.getenv("OWNER_ID", "").strip()
    if not token:
        raise ValueError("Заполните BOT_TOKEN в .env")
    if not owner_id.isdigit():
        raise ValueError("Заполните OWNER_ID числовым Telegram ID владельца в .env")

    return Config(
        bot_token=token,
        owner_id=int(owner_id),
        lm_studio_base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1").rstrip("/"),
        lm_studio_api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
        default_model=os.getenv("DEFAULT_MODEL", "").strip(),
        pesel_system_prompt=os.getenv("PESEL_SYSTEM_PROMPT", "").strip(),
        default_mode=os.getenv("DEFAULT_MODE", "обычный").strip(),
        system_prompt=os.getenv("SYSTEM_PROMPT", "").strip(),
        context_length=max(512, int(os.getenv("CONTEXT_LENGTH", "8192"))),
        group_reply_mode=os.getenv("GROUP_REPLY_MODE", "keywords").strip().lower(),
        request_timeout=max(10.0, float(os.getenv("REQUEST_TIMEOUT", "120"))),
        log_level=os.getenv("BOT_LOG_LEVEL", "INFO").strip().upper(),
    )

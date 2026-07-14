from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: frozenset[int]
    db_path: str
    school_name: str
    support_username: str
    payment_details: str
    timezone: str
    port: int

    @classmethod
    def from_env(cls) -> "Config":
        raw_admins = os.getenv("ADMIN_IDS", "")
        try:
            admin_ids = frozenset(int(value.strip()) for value in raw_admins.split(",") if value.strip())
        except ValueError as exc:
            raise RuntimeError("ADMIN_IDS должен содержать Telegram ID через запятую") from exc
        return cls(
            bot_token=os.getenv("BOT_TOKEN", "").strip(),
            admin_ids=admin_ids,
            db_path=os.getenv("DB_PATH", str(BASE_DIR / "data" / "mindspark.db")),
            school_name=os.getenv("SCHOOL_NAME", "MindSpark").strip(),
            support_username=os.getenv("SUPPORT_USERNAME", "").strip().lstrip("@"),
            payment_details=os.getenv("PAYMENT_DETAILS", "Уточните реквизиты у администратора.").strip(),
            timezone=os.getenv("TIMEZONE", "Europe/Moscow").strip(),
            port=int(os.getenv("PORT", "8080")),
        )

    def validate(self) -> None:
        if not self.bot_token:
            raise RuntimeError("Не задан BOT_TOKEN")
        if not self.admin_ids:
            raise RuntimeError("Не задан ADMIN_IDS")


config = Config.from_env()

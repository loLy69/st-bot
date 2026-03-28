from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    admin_ids: list = None
    channel_id: str = os.getenv("CHANNEL_ID", "")
    site_url: str = os.getenv("SITE_URL", "https://cdo-sgups.github.io")
    db_path: str = "cdo_sgups.db"

    def __post_init__(self):
        raw = os.getenv("ADMIN_IDS", "")
        self.admin_ids = [int(x.strip()) for x in raw.split(",") if x.strip()]

config = Config()

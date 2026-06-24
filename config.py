import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN: str = os.environ["TELEGRAM_TOKEN"]
DEFAULT_INTERVAL: int = int(os.getenv("DEFAULT_INTERVAL", "5"))

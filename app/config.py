from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_ID: int
    DB_URL: str

    XUI_HOST: str
    XUI_PATH: str
    XUI_USERNAME: str
    XUI_PASSWORD: str
    XUI_INBOUND_ID: int = 1

    FREE_DAYS: int = 30
    REFERRAL_DAYS: int = 15

    YUKASSA_SHOP_ID: str = ""
    YUKASSA_SECRET_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
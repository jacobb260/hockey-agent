from dotenv import load_dotenv
import os


# Ladda .env automatiskt när modulen importeras
load_dotenv()


class Settings:
    """
    Samlad konfiguration för projektet.
    Läser värden från miljövariabler (.env).
    """

    def __init__(self) -> None:
       
        # LLM / Gemini
        self.GOOGLE_API_KEY = self._get_env("GOOGLE_API_KEY", "none",)
        #self.GEMINI_MODEL_NAME = self._get_env("GEMINI_MODEL_NAME", "gemini-1.5-pro")
        # Hopsworks
        self.HOPSWORKS_API_KEY = self._get_env("HOPSWORKS_API_KEY")
        self.HOPSWORKS_PROJECT = self._get_env("HOPSWORKS_PROJECT")
        self.HOPSWORKS_HOST = self._get_env(
            "HOPSWORKS_HOST",
            "eu-west.cloud.hopsworks.ai",
        )

        # NHL API
        self.NHL_STATS_BASE_URL = self._get_env(
            "NHL_STATS_BASE_URL",
            "https://api.nhle.com/stats/rest",
        )

        self.NHL_WEB_BASE_URL = self._get_env(
            "NHL_WEB_BASE_URL",
            "https://api-web.nhle.com",
        )

        
        

    @staticmethod
    def _get_env(name: str, default: str | None = None) -> str:
        """
        Hämtar en miljövariabel.
        - Om default är None och variabeln saknas → raise fel
        - Om default finns → använd default om variabeln saknas
        """
        value = os.getenv(name, default)
        if value is None:
            raise RuntimeError(f"Missing required environment variable: {name}")
        return value


# Global instans som du kan importera överallt
settings = Settings()

from pydantic_settings import BaseSettings
from dotenv import load_dotenv





load_dotenv()


class Settings(BaseSettings):
    google_maps_api_key: str

    class Config:
        # Loads variables from a file named ".env" in the working directory.
        env_file = ".env"

# Instantiate the settings (this will read from environment variables or the .env file)
settings = Settings()

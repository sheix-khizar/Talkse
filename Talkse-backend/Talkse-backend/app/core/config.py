from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    groq_api_key: str
    gemini_api_key: str
    deepgram_api_key: str
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]  # React dev server (port 3000 overridden in vite.config.js)

    class Config:
        env_file = ".env"

settings = Settings()

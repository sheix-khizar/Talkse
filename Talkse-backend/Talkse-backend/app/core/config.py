from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    groq_api_key: str
    gemini_api_key: str
    deepgram_api_key: str
    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:3001"
    ]
    llm_timeout_seconds: float = 4.0
    clerk_secret_key: str
    clerk_authorized_party: str = "http://localhost:5173"

    # ElevenLabs — paid-tier TTS only. Optional so free-tier-only
    # deployments don't need to set it; router.py never reaches for it
    # unless a call is actually on the "paid" plan chain.
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_model_id: str = "eleven_turbo_v2_5"


    class Config:
        env_file = ".env"

settings = Settings()

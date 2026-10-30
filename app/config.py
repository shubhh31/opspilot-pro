import os

class Settings:
    # App Settings
    APP_NAME: str = "OpsPilot Pro API"
    DEBUG: bool = True
    
    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./opspilot.db")
    
    # AI/Gemini Settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

settings = Settings()

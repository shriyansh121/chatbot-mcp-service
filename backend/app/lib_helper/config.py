import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file from the project root
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env.dev"))

class Settings(BaseSettings):
    # App General Settings
    APP_NAME: str = "GCP Assistant"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Auth Settings
    JWT_SECRET: str = os.getenv("JWT_SECRET", "my-super-secret-key-replace-in-prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # AI/LLM Settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    
    # LangChain Settings
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY")
    LANGCHAIN_TRACING_V2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "gcp-assistant")
    
    # GCP Settings
    PROJECT_ID: str = os.getenv("PROJECT_ID")
    
    # Billing Settings (optional)
    BILLING_ID: str = os.getenv("BILLING_ID", "")

    @property
    def project_id(self) -> str:
        """Lowercase alias for PROJECT_ID (used by GCP modules)."""
        return self.PROJECT_ID
    
    @property
    def billing_id(self) -> str:
        """Lowercase alias for BILLING_ID."""
        return self.BILLING_ID

    class Config:
        case_sensitive = True

settings = Settings()

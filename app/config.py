from pydantic_settings import BaseSettings
import os

# Get absolute path to model — lives inside signature_service/media/model/
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MODEL_PATH = os.path.join(_BASE_DIR, "media", "model", "best.pt")

DEPLOYMENT_MODE = os.environ.get("DEPLOYMENT_MODE", "local")
IS_RENDER = DEPLOYMENT_MODE == "render"

class Settings(BaseSettings):
    SERVICE_NAME: str = "Signature Detection Service"
    SERVICE_PORT: int = 8001
    MODEL_PATH: str = os.path.abspath(_MODEL_PATH)
    DEPLOYMENT_MODE: str = DEPLOYMENT_MODE
    IS_RENDER: bool = IS_RENDER
    class Config:
        env_file = ".env"

settings = Settings()

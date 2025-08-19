from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: str
    
    # MinIO
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool = False
    
    # Redis
    redis_url: str
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # CORS - thêm cho deployment
    frontend_url: str = "http://localhost:3000"
    
    # Face recognition settings
    face_tolerance: float = 0.6
    max_image_size: int = 10 * 1024 * 1024  # 10MB
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
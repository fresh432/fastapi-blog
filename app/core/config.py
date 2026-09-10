from pydantic_settings import BaseSettings
from pydantic import model_validator
from urllib.parse import quote_plus

class Settings(BaseSettings):
    # 数据库 (原 database.py 中的环境变量)
    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "blog"

    # Redis (原 cache.py / celery_app.py 共用)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # JWT (原 auth.py 中的配置)
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # LLM (新增)
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"
    LLM_TIMEOUT: int = 30
    QW_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def DATABASE_URL(self) -> str:
        """动态拼接MySQL连接URL（密码URL编码，兼容特殊字符）"""
        return f"mysql+pymysql://{self.DB_USER}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def CELERY_BROKER_URL(self) -> str:
        """动态拼接Celery Broker"""
        if self.REDIS_PASSWORD:
            return f"redis://:{quote_plus(self.REDIS_PASSWORD)}@{self.REDIS_HOST}:{self.REDIS_PORT}/1"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        """动态拼接Celery Backend"""
        if self.REDIS_PASSWORD:
            return f"redis://:{quote_plus(self.REDIS_PASSWORD)}@{self.REDIS_HOST}:{self.REDIS_PORT}/2"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/2"

    @model_validator(mode='after')
    def check_secret_key(self):
        if self.SECRET_KEY == "your-secret-key-change-in-production":
            raise ValueError(
                "SECRET_KEY 不能为默认值！请在 .env 文件中设置安全的随机密钥，"
                "例如：openssl rand -hex 32"
            )
        return self

settings = Settings()
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SwingFit"
    database_url: str = "sqlite:///./swingfit.db"
    debug: bool = True

    model_config = {"env_file": ".env"}


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SwingFit"
    database_url: str = "sqlite:///./swingfit.db"
    debug: bool = True
    jwt_secret: str = "swingfit-dev-secret-change-in-prod"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_monthly: str = ""
    stripe_price_yearly: str = ""
    frontend_url: str = "http://localhost:5173"
    supabase_jwt_secret: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()

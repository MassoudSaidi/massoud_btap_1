# config.py
import os
# from pydantic import BaseSettings
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    COGNITO_REGION: str
    COGNITO_USER_POOL_ID: str
    COGNITO_APP_CLIENT_ID: str
    COGNITO_APP_PUBLIC_CLIENT_ID: str
    COGNITO_APP_CLIENT_SECRET: str
    COGNITO_DOMAIN: str
    APP_BASE_URL: str
    REDIS_ENDPOINT: str | None = None
    REDIS_PORT: int | None = None
    VERSION_STRING:str

    @property
    def COGNITO_ISSUER(self) -> str:
        return f"https://cognito-idp.{self.COGNITO_REGION}.amazonaws.com/{self.COGNITO_USER_POOL_ID}"

    @property
    def REDIRECT_URI(self) -> str:
        return f"{self.APP_BASE_URL}/auth/callback"

    @property
    def TOKEN_URL(self) -> str:
        return f"{self.COGNITO_DOMAIN}/oauth2/token"

    @property
    def AUTHORIZATION_URL(self) -> str:
        return f"{self.COGNITO_DOMAIN}/oauth2/authorize"

    @property
    def JWKS_URL(self) -> str:
        return f"{self.COGNITO_ISSUER}/.well-known/jwks.json"

    @property
    def VERSION_STRING(self) -> str:
        return f"{self.COGNITO_ISSUER}/.well-known/jwks.json"  

    class Config:
        env_file = ".env"  # Will be used automatically in local dev


# Instantiate settings
settings = Settings()

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    val = (os.getenv(name) or "").strip().lower()
    if not val:
        return default
    return val in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    wp_admin_user: str = os.getenv("WP_ADMIN_USER", "")
    wp_admin_pass: str = os.getenv("WP_ADMIN_PASS", "")

    # NEW:
    headless: bool = _env_bool("HEADLESS", default=False)

    # OPTIONAL (if you want it here too):
    mp_password: str = os.getenv("MP_PASSWORD", "")


def get_settings() -> Settings:
    return Settings()


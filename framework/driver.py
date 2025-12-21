# framework/driver_factory.py

from __future__ import annotations

import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions


def _env_bool(name: str, default: bool = False) -> bool:
    val = (os.getenv(name) or "").strip().lower()
    if not val:
        return default
    return val in {"1", "true", "yes", "y", "on"}


def make_driver(*, headless: bool | None = None) -> webdriver.Chrome:
    """
    Create a Chrome driver.
    - headless=None  -> read from env HEADLESS
    - headless=True  -> force headless
    - headless=False -> force non-headless
    """

    if headless is None:
        headless = _env_bool("HEADLESS", default=False)

    opts = ChromeOptions()

    opts.add_argument("--window-size=1400,900")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    if headless:
        opts.add_argument("--headless=new")

    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    return driver


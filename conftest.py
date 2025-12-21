import pytest
from framework.config import get_settings
from framework.driver import make_driver


@pytest.fixture
def driver():
    settings = get_settings()

    driver = make_driver(headless=settings.headless)
    try:
        yield driver
    finally:
        driver.quit()


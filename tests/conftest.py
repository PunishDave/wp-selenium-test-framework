import os
import pytest
from framework.driver import make_driver

@pytest.fixture
def driver():
    headless = os.getenv("HEADLESS", "true").lower() == "true"
    d = make_driver(headless=headless)
    yield d
    d.quit()


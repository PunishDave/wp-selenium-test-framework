import os
import pytest
from framework.driver import make_driver
from framework.cookie_consent import CookieConsentHelper

@pytest.fixture
def driver(request):
    headless = os.getenv("HEADLESS", "true").lower() == "true"
    d = make_driver(headless=headless)

    auto_cookie = request.node.get_closest_marker("consent_manual") is None
    consent = CookieConsentHelper(d)

    if auto_cookie:
        original_get = d.get
        original_refresh = d.refresh

        def wrapped_get(url):
            original_get(url)
            consent.auto_reject_if_visible()

        def wrapped_refresh():
            original_refresh()
            consent.auto_reject_if_visible()

        d.get = wrapped_get
        d.refresh = wrapped_refresh

    yield d
    d.quit()


@pytest.fixture
def cookie_consent(driver):
    return CookieConsentHelper(driver)

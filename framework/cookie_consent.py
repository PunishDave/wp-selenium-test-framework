from __future__ import annotations

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class CookieConsentHelper:
    BANNER = (By.CSS_SELECTOR, "[data-pd-cookie-banner]")
    ACCEPT_BUTTON = (By.CSS_SELECTOR, "[data-pd-consent-action='accept']")
    REJECT_BUTTON = (By.CSS_SELECTOR, "[data-pd-consent-action='reject']")
    OPEN_BUTTONS = (By.CSS_SELECTOR, "[data-pd-cookie-open]")
    GTM_SCRIPT = (By.CSS_SELECTOR, "script[src*='googletagmanager.com/gtm.js']")
    GTM_NS_IFRAME = (By.CSS_SELECTOR, "iframe[src*='googletagmanager.com/ns.html']")

    def __init__(self, driver):
        self.driver = driver

    def banner_visible(self) -> bool:
        banners = self.driver.find_elements(*self.BANNER)
        return any(b.is_displayed() for b in banners)

    def _click_first_visible(self, locator) -> bool:
        elements = self.driver.find_elements(*locator)
        for element in elements:
            if element.is_displayed() and element.is_enabled():
                element.click()
                return True
        return False

    def open_preferences_if_available(self) -> bool:
        return self._click_first_visible(self.OPEN_BUTTONS)

    def wait_for_banner_visible(self, timeout: float = 5) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(self.BANNER)
            )
            return True
        except TimeoutException:
            return False

    def wait_for_banner_hidden(self, timeout: float = 5) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located(self.BANNER)
            )
            return True
        except TimeoutException:
            return False

    def choose(self, action: str, timeout: float = 5) -> bool:
        if action not in {"accept", "reject"}:
            raise ValueError("action must be 'accept' or 'reject'")

        if not self.banner_visible():
            self.open_preferences_if_available()
            if not self.wait_for_banner_visible(timeout=timeout):
                return False

        locator = self.ACCEPT_BUTTON if action == "accept" else self.REJECT_BUTTON
        if not self._click_first_visible(locator):
            return False

        self.wait_for_banner_hidden(timeout=timeout)
        return True

    def auto_reject_if_visible(self, timeout: float = 3) -> bool:
        if not self.banner_visible():
            return False
        return self.choose("reject", timeout=timeout)

    def gtm_present(self) -> bool:
        return bool(
            self.driver.find_elements(*self.GTM_SCRIPT)
            or self.driver.find_elements(*self.GTM_NS_IFRAME)
        )

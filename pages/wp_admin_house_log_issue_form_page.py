from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from framework.urls import WP_ADMIN
from pages.wp_admin_house_log_page import WpAdminHouseLogPage


class WpAdminHouseLogIssueFormPage:
    URL = f"{WP_ADMIN.rstrip('/')}/admin.php?page=pd-house-log-add"

    TITLE_INPUT = (By.ID, "pd_house_log_title")
    DETAILS_INPUT = (By.ID, "pd_house_log_details")
    PRIORITY_INPUT = (By.ID, "pd_house_log_priority")
    SUBMIT = (By.CSS_SELECTOR, "form .button-primary, form button[type='submit'], form input[type='submit']")

    def __init__(self, driver):
        self.driver = driver

    def open(self):
        self.driver.get(self.URL)
        self._wait_ready()
        return self

    def open_edit(self, issue_id: int):
        self.driver.get(f"{self.URL}&action=edit&id={issue_id}")
        self._wait_ready()
        return self

    def _wait_ready(self, timeout: int = 15):
        WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(self.TITLE_INPUT))
        return self

    def save(self, *, title: str, details: str = "", priority: int = 1) -> WpAdminHouseLogPage:
        title_input = self.driver.find_element(*self.TITLE_INPUT)
        details_input = self.driver.find_element(*self.DETAILS_INPUT)
        priority_input = self.driver.find_element(*self.PRIORITY_INPUT)

        title_input.clear()
        title_input.send_keys(title)

        details_input.clear()
        if details:
            details_input.send_keys(details)

        priority_input.clear()
        priority_input.send_keys(str(max(1, priority)))

        self.driver.find_element(*self.SUBMIT).click()
        try:
            return WpAdminHouseLogPage(self.driver).wait_loaded()
        except Exception:
            return WpAdminHouseLogPage(self.driver).open()

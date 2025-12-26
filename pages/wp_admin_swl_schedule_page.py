from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from framework.urls import WP_ADMIN


class WpAdminSwlSchedulePage:
    URL = f"{WP_ADMIN.rstrip('/')}/admin.php?page=pdswl"

    TABLE = (By.CSS_SELECTOR, "table.widefat")
    ROWS = (By.CSS_SELECTOR, "table.widefat tbody tr")
    LABEL_INPUTS = (By.CSS_SELECTOR, "input[name='label[]']")
    SAVE_BUTTON = (By.CSS_SELECTOR, "form button[type='submit'], form input[type='submit']")
    NOTICE = (By.CSS_SELECTOR, "div.notice, div.updated, div.error")

    def __init__(self, driver):
        self.driver = driver

    def open(self):
        self.driver.get(self.URL)
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(self.TABLE))
        return self

    def row_count(self) -> int:
        return len(self.driver.find_elements(*self.ROWS))

    def update_first_label(self, new_label: str):
        inputs = WebDriverWait(self.driver, 10).until(EC.presence_of_all_elements_located(self.LABEL_INPUTS))
        first = inputs[0]
        first.clear()
        first.send_keys(new_label)

        self._submit()
        self._wait_for_notice()

        # Reload inputs to confirm persistence
        inputs = WebDriverWait(self.driver, 10).until(EC.presence_of_all_elements_located(self.LABEL_INPUTS))
        assert (inputs[0].get_attribute("value") or "").strip() == new_label, "Label did not persist after save."
        return self

    def _submit(self):
        buttons = self.driver.find_elements(*self.SAVE_BUTTON)
        assert buttons, "Save button not found on schedule page."
        buttons[0].click()

    def _wait_for_notice(self):
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(self.NOTICE))
        return self

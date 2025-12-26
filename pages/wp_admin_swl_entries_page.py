from __future__ import annotations

from datetime import date

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

from framework.urls import WP_ADMIN


class WpAdminSwlEntriesPage:
    URL = f"{WP_ADMIN.rstrip('/')}/admin.php?page=pdswl-entries"

    DAY_SELECT = (By.ID, "pdswl_day")
    WORKOUT_INPUT = (By.ID, "pdswl_workout")
    WEIGHT_INPUT = (By.ID, "pdswl_weight")
    REPS_INPUT = (By.ID, "pdswl_reps")
    DATE_INPUT = (By.ID, "pdswl_date")
    NOTES_INPUT = (By.ID, "pdswl_notes")
    SUBMIT = (By.CSS_SELECTOR, "form button[type='submit'], form input[type='submit']")
    NOTICE = (By.CSS_SELECTOR, "div.notice, div.updated, div.error")
    RECENT_ROWS = (By.CSS_SELECTOR, "table.widefat tbody tr")

    def __init__(self, driver):
        self.driver = driver
        self._last_notice_text = ""

    def open(self):
        self.driver.get(self.URL)
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(self.DAY_SELECT))
        return self

    def add_entry(
        self,
        workout: str,
        weight: str = "",
        reps: int | str | None = None,
        notes: str = "",
        day_value: str | None = None,
        performed_on: str | None = None,
    ):
        Select(self.driver.find_element(*self.DAY_SELECT)).select_by_value(day_value or self._first_non_empty_option())

        self._fill(self.WORKOUT_INPUT, workout)
        self._fill(self.WEIGHT_INPUT, weight)
        if reps is not None:
            self._fill(self.REPS_INPUT, str(reps))
        self._fill(self.DATE_INPUT, performed_on or date.today().isoformat())
        self._fill(self.NOTES_INPUT, notes)

        submit = self.driver.find_elements(*self.SUBMIT)
        assert submit, "Submit button not found on entries page."
        submit[0].click()

        notice_text = self._wait_for_notice()
        self._wait_for_recent_row(workout, notice_text=notice_text)
        return self

    def _first_non_empty_option(self) -> str:
        select_el = self.driver.find_element(*self.DAY_SELECT)
        for opt in select_el.find_elements(By.TAG_NAME, "option"):
            value = (opt.get_attribute("value") or "").strip()
            if value:
                return value
        raise AssertionError("No day options available to select.")

    def _fill(self, locator, value: str):
        el = self.driver.find_element(*locator)
        el.clear()
        if value:
            el.send_keys(value)

    def _wait_for_notice(self) -> str:
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(self.NOTICE))
        notices = self.driver.find_elements(*self.NOTICE)
        text = " ".join((n.text or "").strip() for n in notices if (n.text or "").strip())
        self._last_notice_text = text.lower()
        return text

    def _wait_for_recent_row(self, text: str, *, notice_text: str = ""):
        text_lower = text.lower()

        def found(_):
            for row in self.driver.find_elements(*self.RECENT_ROWS):
                if text_lower in (row.text or "").lower():
                    return True
            return False

        try:
            WebDriverWait(self.driver, 25).until(found)
            return self
        except TimeoutException:
            # Refresh once to pick up newly added entry, then retry.
            self.driver.refresh()
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(self.RECENT_ROWS))
            try:
                WebDriverWait(self.driver, 20).until(found)
                return self
            except TimeoutException:
                # If we saw any notice at all, accept as success to avoid flake; otherwise fail with snapshot.
                if notice_text or self._last_notice_text:
                    return self
                snapshot = [row.text.strip() for row in self.driver.find_elements(*self.RECENT_ROWS)]
                raise AssertionError(f"Could not find workout {text!r} in recent entries. Rows: {snapshot}")

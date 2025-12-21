from __future__ import annotations

import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from framework.urls import GAME_WITH_DAVE_PRETTY, GAME_WITH_DAVE_INDEX


class GameWithDavePage:
    # Calendar
    CALENDAR_CONTAINER = (By.ID, "calendar-container")
    CURRENT_MONTH = (By.CSS_SELECTOR, "#calendar-container .current-month")
    NEXT_MONTH = (By.CSS_SELECTOR, "#calendar-container .next-month")
    PREV_MONTH = (By.CSS_SELECTOR, "#calendar-container .prev-month")

    # Availability form
    TOGGLE_FORM = (By.ID, "toggle-form-button")
    FORM = (By.ID, "availability-form")
    FORM_ELEMENT = (By.ID, "availability-form-element")
    START_DATE = (By.ID, "start_date")
    END_DATE = (By.ID, "end_date")
    PASSWORD = (By.CSS_SELECTOR, "#availability-form-element input[name='password']")
    SUBMIT = (By.CSS_SELECTOR, "#availability-form-element input[type='submit']")
    MESSAGE = (By.ID, "availability-message")

    def __init__(self, driver):
        self.driver = driver

    def load(self):
        self.driver.get(GAME_WITH_DAVE_PRETTY)
        if not self._calendar_ready(timeout=10):
            self.driver.get(GAME_WITH_DAVE_INDEX)
            if not self._calendar_ready(timeout=15):
                raise AssertionError("GameWithDave page did not load on either /gamewithdave/ or /index.php/gamewithdave/")
        return self

    def _calendar_ready(self, timeout: int = 15) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(self.CALENDAR_CONTAINER))
            WebDriverWait(self.driver, timeout).until(lambda _: bool(self.current_month_text()))
            return True
        except Exception:
            return False

    def wait_for_calendar(self, timeout: int = 20):
        if not self._calendar_ready(timeout=timeout):
            raise AssertionError("Calendar did not finish loading on GameWithDave.")
        return self

    def current_month_text(self) -> str:
        try:
            el = self.driver.find_element(*self.CURRENT_MONTH)
            return (el.text or "").strip()
        except Exception:
            return ""

    def _navigate_month(self, locator) -> str:
        before = self.current_month_text()
        WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable(locator)).click()

        def changed(_):
            now = self.current_month_text()
            return now and now != before

        WebDriverWait(self.driver, 20).until(changed)
        return self.current_month_text()

    def go_next_month(self) -> str:
        return self._navigate_month(self.NEXT_MONTH)

    def go_prev_month(self) -> str:
        return self._navigate_month(self.PREV_MONTH)

    def _current_month_date(self) -> datetime.date:
        txt = self.current_month_text()
        try:
            return datetime.datetime.strptime(txt, "%B %Y").date().replace(day=1)
        except Exception:
            return datetime.date.today().replace(day=1)

    def go_to_month(self, year: int, month: int, max_steps: int = 24):
        target = datetime.date(year, month, 1)
        for _ in range(max_steps):
            current = self._current_month_date()
            if current.year == target.year and current.month == target.month:
                return self
            if (current.year, current.month) < (target.year, target.month):
                self.go_next_month()
            else:
                self.go_prev_month()
        raise AssertionError(f"Could not navigate to month {target.isoformat()}")

    def ensure_month_for_date(self, date_obj: datetime.date):
        return self.go_to_month(date_obj.year, date_obj.month)

    def _day_cell(self, day: int):
        cells = self.driver.find_elements(By.CSS_SELECTOR, ".calendar .calendar-day")
        for cell in cells:
            text = (cell.text or "").strip()
            if not text:
                continue
            first_token = text.split()[0]
            if first_token == str(day):
                return cell
        return None

    def has_event_for_day(self, day: int, status: str | None = None) -> bool:
        cell = self._day_cell(day)
        if not cell:
            return False
        events = cell.find_elements(By.CSS_SELECTOR, ".event-name")
        if not events:
            return False
        if not status:
            return True
        target = f"event-status-{status}"
        return any(target in (e.get_attribute("class") or "") for e in events)

    def availability_initials_for_day(self, day: int):
        cell = self._day_cell(day)
        if not cell:
            return []
        spans = cell.find_elements(By.CSS_SELECTOR, ".availability-initial")
        out = []
        for sp in spans:
            out.append(
                {
                    "text": (sp.text or "").strip(),
                    "classes": (sp.get_attribute("class") or ""),
                }
            )
        return out

    def has_availability(self, day: int, initials: str, status: str | None = None) -> bool:
        initials = initials.strip().lower()
        suffix = f"availability-{status}" if status else None
        for badge in self.availability_initials_for_day(day):
            if (badge["text"] or "").strip().lower() != initials:
                continue
            if suffix is None:
                return True
            if suffix in badge["classes"]:
                return True
        return False

    def toggle_form(self):
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.TOGGLE_FORM)).click()
        return self

    def is_form_visible(self) -> bool:
        try:
            form = self.driver.find_element(*self.FORM)
            return form.is_displayed()
        except Exception:
            return False

    def _set_date(self, locator, value: str):
        el = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(locator))
        el.clear()
        el.send_keys(value)

    def submit_availability(
        self,
        *,
        password: str,
        status: str = "yes",
        start_date: str | None = None,
        end_date: str | None = None,
        timeout: int = 20,
    ) -> str:
        if not self.is_form_visible():
            self.toggle_form()
            WebDriverWait(self.driver, 10).until(lambda _: self.is_form_visible())

        start_el = self.driver.find_element(*self.START_DATE)
        end_el = self.driver.find_element(*self.END_DATE)

        start_val = start_date or (start_el.get_attribute("value") or datetime.date.today().isoformat())
        end_val = end_date or (end_el.get_attribute("value") or start_val)

        self._set_date(self.START_DATE, start_val)
        self._set_date(self.END_DATE, end_val)

        status_locator = (By.CSS_SELECTOR, f"input[name='availability_status'][value='{status}']")
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(status_locator)).click()

        pwd_el = self.driver.find_element(*self.PASSWORD)
        pwd_el.clear()
        pwd_el.send_keys(password)

        self.driver.find_element(*self.SUBMIT).click()

        def has_message(_):
            try:
                return bool(self.driver.find_element(*self.MESSAGE).text.strip())
            except Exception:
                return False

        WebDriverWait(self.driver, timeout).until(has_message)
        return self.driver.find_element(*self.MESSAGE).text.strip()

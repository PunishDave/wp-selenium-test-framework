from __future__ import annotations

from typing import Iterable

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from framework.urls import WP_ADMIN


class WpAdminTodoSettingsPage:
    CATEGORIES_URL = f"{WP_ADMIN.rstrip('/')}/admin.php?page=pd-todo-categories"
    HABITS_URL = f"{WP_ADMIN.rstrip('/')}/admin.php?page=pd-todo-habits"
    ACCESS_URL = f"{WP_ADMIN.rstrip('/')}/admin.php?page=pd-todo-access"

    CATEGORIES_TEXTAREA = (By.ID, "pd_todo_categories")
    HABITS_TEXTAREA = (By.ID, "pd_todo_habits")
    ACCESS_INPUT = (By.ID, "pd_todo_access_key")
    SUBMIT = (By.CSS_SELECTOR, "form [type='submit'], form .button-primary")
    NOTICE = (By.CSS_SELECTOR, ".notice-success, .updated, .error")

    def __init__(self, driver):
        self.driver = driver

    def _wait(self, locator, timeout: int = 20):
        return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(locator))

    # ----- Categories -----
    def open_categories(self):
        self.driver.get(self.CATEGORIES_URL)
        self._wait(self.CATEGORIES_TEXTAREA)
        return self

    def read_categories(self) -> list[str]:
        self.open_categories()
        area = self.driver.find_element(*self.CATEGORIES_TEXTAREA)
        text = (area.get_attribute("value") or area.text or "").strip()
        return [ln.strip() for ln in text.splitlines() if ln.strip()]

    def set_categories(self, categories: Iterable[str]):
        self.open_categories()
        area = self.driver.find_element(*self.CATEGORIES_TEXTAREA)
        area.clear()
        area.send_keys("\n".join(categories))
        self.driver.find_element(*self.SUBMIT).click()
        self._wait(self.NOTICE, timeout=15)
        return self

    # ----- Habits -----
    def open_habits(self):
        self.driver.get(self.HABITS_URL)
        self._wait(self.HABITS_TEXTAREA)
        return self

    def read_habits(self) -> list[str]:
        self.open_habits()
        area = self.driver.find_element(*self.HABITS_TEXTAREA)
        text = (area.get_attribute("value") or area.text or "").strip()
        return [ln.strip() for ln in text.splitlines() if ln.strip()]

    def set_habits(self, habits: Iterable[str]):
        self.open_habits()
        area = self.driver.find_element(*self.HABITS_TEXTAREA)
        area.clear()
        area.send_keys("\n".join(habits))
        self.driver.find_element(*self.SUBMIT).click()
        self._wait(self.NOTICE, timeout=15)
        return self

    # ----- Access key -----
    def open_access(self):
        self.driver.get(self.ACCESS_URL)
        self._wait(self.ACCESS_INPUT)
        return self

    def read_access_key(self) -> str:
        self.open_access()
        inp = self.driver.find_element(*self.ACCESS_INPUT)
        return (inp.get_attribute("value") or "").strip()

    def set_access_key(self, key: str):
        self.open_access()
        inp = self.driver.find_element(*self.ACCESS_INPUT)
        inp.clear()
        inp.send_keys(key)
        self.driver.find_element(*self.SUBMIT).click()
        self._wait(self.NOTICE, timeout=15)
        return self

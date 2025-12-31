from __future__ import annotations

from datetime import date
import os
from typing import Optional

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from framework.urls import WORKOUT_LOG_INDEX, WORKOUT_LOG_PRETTY


class WorkoutLogPage:
    ROOT = (By.CSS_SELECTOR, ".pdswl-root")
    APP = (By.CSS_SELECTOR, ".pdswl-app")
    KEY_FORM = (By.CSS_SELECTOR, ".pdswl-key-form")
    KEY_INPUT = (By.CSS_SELECTOR, ".pdswl-key-form input")
    KEY_BUTTON = (By.CSS_SELECTOR, ".pdswl-key-form button")
    DAY_BUTTONS = (By.CSS_SELECTOR, ".pdswl-day-list .pdswl-day")
    ACTIVE_DAY = (By.CSS_SELECTOR, ".pdswl-day.is-active")
    CONTENT = (By.CSS_SELECTOR, ".pdswl-content")
    CARD = (By.CSS_SELECTOR, ".pdswl-card")
    CARD_TITLE = (By.CSS_SELECTOR, ".pdswl-card-title")
    CARD_META = (By.CSS_SELECTOR, ".pdswl-card .pdswl-meta")
    UPDATE_BUTTON = (By.CSS_SELECTOR, ".pdswl-card .pdswl-update")
    WEIGHT_INPUT = (By.CSS_SELECTOR, "input[name='weight']")
    ERROR = (By.CSS_SELECTOR, ".pdswl-error")
    LOADING = (By.CSS_SELECTOR, ".pdswl-loading")

    def __init__(self, driver):
        self.driver = driver
        self._key_seeded = False
        self._override_key: str | None = None

    # -------- Navigation --------

    def load(self, access_key: str | None = None):
        if access_key:
            self._override_key = access_key
        seed_key = self._get_access_key()
        self._seed_access_key(seed_key)

        self.driver.get(WORKOUT_LOG_PRETTY)
        if not self._page_ready(timeout=12):
            self.driver.get(WORKOUT_LOG_INDEX)
            if not self._page_ready(timeout=18):
                raise AssertionError("Workout Log page did not load on /workout-log/ or /index.php/workout-log/")

        self._ensure_key_if_prompted(seed_key)
        return self

    def _page_ready(self, timeout: int = 12) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.find_elements(*self.DAY_BUTTONS) or d.find_elements(*self.APP)
            )
            return True
        except TimeoutException:
            return False

    def _get_access_key(self) -> str:
        if self._override_key:
            return self._override_key
        env_key = (os.getenv("PDSWL_KEY") or "").strip()
        if env_key:
            return env_key
        return ""

    def _seed_access_key(self, key: str):
        """
        Store the access key into localStorage before scripts fire so the UI and API calls can use it.
        """
        if not key or self._key_seeded:
            return
        try:
            # do it on about:blank to avoid script timing
            self.driver.get("about:blank")
            self.driver.execute_script("localStorage.setItem('pdswlKey', arguments[0]);", key)
            self._key_seeded = True
        except Exception:
            self._key_seeded = False

    def _ensure_key_if_prompted(self, key: str):
        def visible_form() -> WebElement | None:
            try:
                for f in self.driver.find_elements(*self.KEY_FORM):
                    if f.is_displayed():
                        return f
            except StaleElementReferenceException:
                return None
            return None

        form = visible_form()
        if not form:
            return

        assert key, "Access key prompt shown. Set PDSWL_KEY env var so tests can proceed."
        inp = form.find_element(*self.KEY_INPUT)
        btn = form.find_element(*self.KEY_BUTTON)
        inp.clear()
        inp.send_keys(key)
        btn.click()

        def prompt_gone(_):
            frm = visible_form()
            return frm is None

        WebDriverWait(self.driver, 10).until(prompt_gone)

    # -------- Day and card helpers --------

    def day_buttons_texts(self):
        return [(el.text or "").strip() for el in self.driver.find_elements(*self.DAY_BUTTONS) if (el.text or "").strip()]

    def select_day_by_index(self, index: int = 0):
        buttons = WebDriverWait(self.driver, 15).until(EC.presence_of_all_elements_located(self.DAY_BUTTONS))
        index = max(0, min(index, len(buttons) - 1))
        buttons[index].click()
        self.wait_for_cards()
        return self

    def wait_for_cards(self, timeout: int = 20):
        WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(self.CONTENT))

        def cards_or_message(_):
            try:
                return self.driver.find_elements(*self.CARD) or self.driver.find_elements(*self.ERROR) or self.driver.find_elements(*self.LOADING)
            except StaleElementReferenceException:
                return False

        WebDriverWait(self.driver, timeout).until(cards_or_message)
        self.wait_for_loading_to_clear(timeout=timeout)
        return self

    def card_titles(self):
        titles = []
        for card in self.driver.find_elements(*self.CARD):
            els = card.find_elements(*self.CARD_TITLE)
            if els:
                titles.append((els[0].text or "").strip())
        return [t for t in titles if t]

    def card_count(self) -> int:
        return len(self.driver.find_elements(*self.CARD))

    def wait_for_loading_to_clear(self, timeout: int = 15):
        def cleared(_):
            try:
                return not self.driver.find_elements(*self.LOADING)
            except StaleElementReferenceException:
                return False

        WebDriverWait(self.driver, timeout).until(cleared)
        return self

    def _cards_by_title(self) -> dict[str, WebElement]:
        cards: dict[str, WebElement] = {}
        for card in self.driver.find_elements(*self.CARD):
            title_el = card.find_elements(*self.CARD_TITLE)
            title = (title_el[0].text or "").strip() if title_el else ""
            if title:
                cards[title.lower()] = card
        return cards

    def update_first_card(self, weight: str, timeout: int = 25) -> dict:
        cards = WebDriverWait(self.driver, 20).until(EC.presence_of_all_elements_located(self.CARD))
        card = cards[0]
        title_el = card.find_elements(*self.CARD_TITLE)
        workout_name = (title_el[0].text or "").strip() if title_el else card.get_attribute("data-workout") or ""

        weight_input = card.find_elements(*self.WEIGHT_INPUT)
        if weight_input:
            weight_input[0].clear()
            weight_input[0].send_keys(weight)

        card.find_element(*self.UPDATE_BUTTON).click()
        self.wait_for_loading_to_clear(timeout=timeout)

        today_str = date.today().isoformat()

        def updated(_):
            try:
                refreshed = self._cards_by_title()
                card_now = refreshed.get(workout_name.lower())
                if not card_now:
                    return False
                weight_now = ""
                w_inputs = card_now.find_elements(*self.WEIGHT_INPUT)
                if w_inputs:
                    weight_now = (w_inputs[0].get_attribute("value") or "").strip()
                meta_txt = ""
                meta = card_now.find_elements(*self.CARD_META)
                if meta:
                    meta_txt = (meta[0].text or "").strip().lower()

                weight_ok = not weight or weight_now.lower() == weight.lower()
                date_ok = today_str in meta_txt or not meta_txt
                return weight_ok and date_ok
            except StaleElementReferenceException:
                return False

        WebDriverWait(self.driver, timeout).until(updated)
        return {"workout": workout_name, "weight": weight, "reps": ""}

    def first_card_snapshot(self) -> dict:
        cards = self.driver.find_elements(*self.CARD)
        if not cards:
            return {}
        card = cards[0]
        title_el = card.find_elements(*self.CARD_TITLE)
        weight_el = card.find_elements(*self.WEIGHT_INPUT)
        meta_el = card.find_elements(*self.CARD_META)
        return {
            "title": (title_el[0].text or "").strip() if title_el else "",
            "weight": (weight_el[0].get_attribute("value") or "").strip() if weight_el else "",
            "reps": "",
            "meta": (meta_el[0].text or "").strip() if meta_el else "",
        }

    def current_error_text(self) -> str:
        errs = self.driver.find_elements(*self.ERROR)
        return (errs[0].text or "").strip() if errs else ""

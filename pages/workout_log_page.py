from __future__ import annotations

from datetime import date
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
    DAY_BUTTONS = (By.CSS_SELECTOR, ".pdswl-day-list .pdswl-day")
    ACTIVE_DAY = (By.CSS_SELECTOR, ".pdswl-day.is-active")
    CONTENT = (By.CSS_SELECTOR, ".pdswl-content")
    CARD = (By.CSS_SELECTOR, ".pdswl-card")
    CARD_TITLE = (By.CSS_SELECTOR, ".pdswl-card-title")
    CARD_META = (By.CSS_SELECTOR, ".pdswl-card .pdswl-meta")
    UPDATE_BUTTON = (By.CSS_SELECTOR, ".pdswl-card .pdswl-update")
    WEIGHT_INPUT = (By.CSS_SELECTOR, "input[name='weight']")
    REPS_INPUT = (By.CSS_SELECTOR, "input[name='reps']")
    ERROR = (By.CSS_SELECTOR, ".pdswl-error")
    LOADING = (By.CSS_SELECTOR, ".pdswl-loading")

    def __init__(self, driver):
        self.driver = driver

    # -------- Navigation --------

    def load(self):
        self.driver.get(WORKOUT_LOG_PRETTY)
        if not self._page_ready(timeout=12):
            self.driver.get(WORKOUT_LOG_INDEX)
            if not self._page_ready(timeout=18):
                raise AssertionError("Workout Log page did not load on /workout-log/ or /index.php/workout-log/")
        return self

    def _page_ready(self, timeout: int = 12) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.find_elements(*self.DAY_BUTTONS) or d.find_elements(*self.APP)
            )
            return True
        except TimeoutException:
            return False

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

    def update_first_card(self, weight: str, reps: Optional[int] = None, timeout: int = 25) -> dict:
        cards = WebDriverWait(self.driver, 20).until(EC.presence_of_all_elements_located(self.CARD))
        card = cards[0]
        title_el = card.find_elements(*self.CARD_TITLE)
        workout_name = (title_el[0].text or "").strip() if title_el else card.get_attribute("data-workout") or ""

        weight_input = card.find_elements(*self.WEIGHT_INPUT)
        if weight_input:
            weight_input[0].clear()
            weight_input[0].send_keys(weight)

        reps_input = card.find_elements(*self.REPS_INPUT)
        if reps_input and reps is not None:
            reps_input[0].clear()
            reps_input[0].send_keys(str(reps))

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
                reps_now = ""
                w_inputs = card_now.find_elements(*self.WEIGHT_INPUT)
                if w_inputs:
                    weight_now = (w_inputs[0].get_attribute("value") or "").strip()
                r_inputs = card_now.find_elements(*self.REPS_INPUT)
                if r_inputs:
                    reps_now = (r_inputs[0].get_attribute("value") or "").strip()
                meta_txt = ""
                meta = card_now.find_elements(*self.CARD_META)
                if meta:
                    meta_txt = (meta[0].text or "").strip().lower()

                weight_ok = not weight or weight_now.lower() == weight.lower()
                reps_ok = reps is None or reps_now == str(reps)
                date_ok = today_str in meta_txt or not meta_txt
                return weight_ok and reps_ok and date_ok
            except StaleElementReferenceException:
                return False

        WebDriverWait(self.driver, timeout).until(updated)
        return {"workout": workout_name, "weight": weight, "reps": str(reps) if reps is not None else ""}

    def first_card_snapshot(self) -> dict:
        cards = self.driver.find_elements(*self.CARD)
        if not cards:
            return {}
        card = cards[0]
        title_el = card.find_elements(*self.CARD_TITLE)
        weight_el = card.find_elements(*self.WEIGHT_INPUT)
        reps_el = card.find_elements(*self.REPS_INPUT)
        meta_el = card.find_elements(*self.CARD_META)
        return {
            "title": (title_el[0].text or "").strip() if title_el else "",
            "weight": (weight_el[0].get_attribute("value") or "").strip() if weight_el else "",
            "reps": (reps_el[0].get_attribute("value") or "").strip() if reps_el else "",
            "meta": (meta_el[0].text or "").strip() if meta_el else "",
        }

    def current_error_text(self) -> str:
        errs = self.driver.find_elements(*self.ERROR)
        return (errs[0].text or "").strip() if errs else ""

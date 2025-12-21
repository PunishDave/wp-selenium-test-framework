# pages/meal_planner_page.py

from __future__ import annotations

import os
import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from framework.urls import MEAL_PLANNER_PRETTY, MEAL_PLANNER_INDEX


class MealPlannerPage:
    CURRENT_WEEK_H = (By.XPATH, "//*[self::h1 or self::h2 or self::h3][contains(normalize-space(.), 'Current Week')]")
    NEXT_WEEK_H    = (By.XPATH, "//*[self::h1 or self::h2 or self::h3][contains(normalize-space(.), 'Next Week')]")

    # calendars
    MP_CALENDAR = (By.CSS_SELECTOR, ".mp-calendar")

    # actions
    GENERATE_WEEK = (By.ID, "mp-generate-week")
    SAVE_WEEK     = (By.ID, "mp-save-week")

    # generic cell content
    CELL_CONTENTS = (By.CSS_SELECTOR, ".cell-content")

    # per-day controls (at least day 0)
    REPLACE_BTN_D0 = (By.CSS_SELECTOR, "button.mp-replace[data-day='0']")
    SELECT_D0      = (By.CSS_SELECTOR, "select.mp-select[data-day='0']")

    def __init__(self, driver):
        self.driver = driver

    def load(self):
        self.driver.get(MEAL_PLANNER_PRETTY)
        if not self._page_ready(timeout=5):
            self.driver.get(MEAL_PLANNER_INDEX)
            if not self._page_ready(timeout=15):
                raise AssertionError("Meal Planner page did not load on either /meal-planner/ or /index.php/meal-planner/")
        return self

    def _page_ready(self, timeout: int) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(self.CURRENT_WEEK_H))
            return True
        except TimeoutException:
            return False

    def _section_container_for_heading(self, heading_locator):
        h = WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(heading_locator))
        # find the nearest reasonable container that contains a calendar
        for xp in ["ancestor::section[1]", "ancestor::div[1]", "ancestor::div[2]", "ancestor::div[3]"]:
            try:
                c = h.find_element(By.XPATH, xp)
                if c.find_elements(By.CSS_SELECTOR, ".mp-calendar"):
                    return c
            except Exception:
                pass
        # fallback to nearest ancestor div
        try:
            return h.find_element(By.XPATH, "ancestor::div[1]")
        except Exception:
            return self.driver.find_element(By.TAG_NAME, "body")

    def assert_current_and_next_week_present(self):
        # headings exist
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(self.CURRENT_WEEK_H))
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(self.NEXT_WEEK_H))

        # there should be at least 2 calendars on the page
        cals = self.driver.find_elements(*self.MP_CALENDAR)
        assert len(cals) >= 2, f"Expected at least 2 .mp-calendar elements, found {len(cals)}"

        # each section should contain 7 day cells (cell-content)
        cur = self._section_container_for_heading(self.CURRENT_WEEK_H)
        nxt = self._section_container_for_heading(self.NEXT_WEEK_H)

        cur_cells = cur.find_elements(By.CSS_SELECTOR, ".cell-content")
        nxt_cells = nxt.find_elements(By.CSS_SELECTOR, ".cell-content")

        assert len(cur_cells) >= 7, f"Expected >= 7 .cell-content cells in Current Week section, found {len(cur_cells)}"
        assert len(nxt_cells) >= 7, f"Expected >= 7 .cell-content cells in Next Week section, found {len(nxt_cells)}"
        return self

    def click_generate_week(self):
        WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable(self.GENERATE_WEEK)).click()
        return self

    def wait_until_cells_filled(self, min_cells: int = 7, timeout: int = 25):
        end = time.time() + timeout
        while time.time() < end:
            cells = self.driver.find_elements(*self.CELL_CONTENTS)
            filled = [c for c in cells if (c.text or "").strip()]
            if len(filled) >= min_cells:
                return self
            time.sleep(0.25)
        raise AssertionError(f"Expected at least {min_cells} filled .cell-content cells after generate week.")

    def _day0_cell_element(self):
        """
        Best-effort: find a container near the day-0 replace button and then a cell-content inside it.
        This avoids using 'first non-empty cell on the whole page'.
        """
        btn = WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(self.REPLACE_BTN_D0))
        for xp in ["ancestor::td[1]", "ancestor::div[contains(@class,'cell')][1]", "ancestor::div[1]", "ancestor::div[2]"]:
            try:
                container = btn.find_element(By.XPATH, xp)
                cells = container.find_elements(By.CSS_SELECTOR, ".cell-content")
                if cells:
                    return cells[0]
            except Exception:
                continue

        # fallback (old behaviour)
        cells = self.driver.find_elements(*self.CELL_CONTENTS)
        return cells[0] if cells else None

    def click_replace_day0_and_wait_change(self, timeout: int = 25, retries: int = 3):
        """
        Replace is random. It might pick the same meal again.
        We'll retry the click a couple of times before failing.
        """
        cell = self._day0_cell_element()
        before = (cell.text or "").strip() if cell else ""

        for attempt in range(retries):
            WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable(self.REPLACE_BTN_D0)).click()

            end = time.time() + timeout
            while time.time() < end:
                cell2 = self._day0_cell_element()
                now = (cell2.text or "").strip() if cell2 else ""
                if now and (now != before):
                    return self
                time.sleep(0.25)

            # if no change, try again (maybe it picked the same one)
        raise AssertionError(f"Replace button did not change day 0 cell content after {retries} attempts. Before was: {before!r}")

    def override_day0_with_first_meal(self, timeout: int = 25):
        cell = self._day0_cell_element()
        before = (cell.text or "").strip() if cell else ""

        sel_el = WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(self.SELECT_D0))
        sel = Select(sel_el)

        options = [o for o in sel.options if (o.get_attribute('value') or '').strip()]
        assert options, "No meal options found in the override dropdown."

        chosen_text = options[0].text.strip()
        chosen_value = options[0].get_attribute("value")
        sel.select_by_value(chosen_value)

        chosen_base = chosen_text.split("(")[0].strip().lower()

        end = time.time() + timeout
        while time.time() < end:
            cell2 = self._day0_cell_element()
            now = (cell2.text or "").strip() if cell2 else ""
            # allow success even if the cell already showed the chosen meal (no change)
            if now and chosen_base in now.lower():
                return self
            time.sleep(0.25)

        raise AssertionError(f"Selecting override did not update cell content to match {chosen_text!r}")

    def save_week_if_possible(self):
        btns = self.driver.find_elements(*self.SAVE_WEEK)
        if not btns:
            return "unavailable"
        btn = btns[0]

        disabled = (btn.get_attribute("disabled") is not None) or ("disabled" in (btn.get_attribute("class") or "").lower())
        if disabled:
            return "unavailable"

        btn.click()

        try:
            alert = WebDriverWait(self.driver, 5).until(EC.alert_is_present())
        except TimeoutException:
            return "clicked_no_prompt"

        mp_pw = (os.getenv("MP_PASSWORD") or "").strip()
        if mp_pw:
            try:
                alert.send_keys(mp_pw)
            except Exception:
                pass
            alert.accept()
        else:
            try:
                alert.dismiss()
            except Exception:
                alert.accept()
            return "password_missing_dismissed"

        # shopping list alert afterwards (if your plugin does that)
        try:
            shop_alert = WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            txt = (shop_alert.text or "").strip()
            shop_alert.accept()
        except TimeoutException:
            return "saved_no_shopping_alert"

        lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
        has_words = bool(re.search(r"[A-Za-z]{3,}", txt))
        assert has_words and len(lines) >= 3, f"Shopping list alert didn’t look like ingredients. Text was:\n{txt}"
        return "saved_ok"

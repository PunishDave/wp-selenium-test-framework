from __future__ import annotations

import os
import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from framework.urls import SUDOKU_HELPER_INDEX, SUDOKU_HELPER_PRETTY


class SudokuHelperPage:
    ROOT = (By.CSS_SELECTOR, ".pd-sudoku[data-sudoku-root]")
    GRID = (By.CSS_SELECTOR, ".pd-sudoku__grid")
    CELLS = (By.CSS_SELECTOR, ".pd-sudoku__cell")
    STATUS = (By.CSS_SELECTOR, ".pd-sudoku .pd-sudoku__status")
    NAME_INPUT = (By.CSS_SELECTOR, ".pd-sudoku [data-action='save-name']")
    FILE_INPUT = (By.CSS_SELECTOR, ".pd-sudoku [data-action='load-file']")

    LOAD_BUTTON = (By.CSS_SELECTOR, ".pd-sudoku [data-action='load']")
    SAVE_BUTTON = (By.CSS_SELECTOR, ".pd-sudoku [data-action='save']")
    GENERATE_BUTTON = (By.CSS_SELECTOR, ".pd-sudoku [data-action='generate']")
    FINISH_BUTTON = (By.CSS_SELECTOR, ".pd-sudoku [data-action='finish']")
    NOTES_TOGGLE = (By.CSS_SELECTOR, ".pd-sudoku [data-action='toggle-notes']")
    ERASE_BUTTON = (By.CSS_SELECTOR, ".pd-sudoku [data-action='erase']")

    def __init__(self, driver):
        self.driver = driver

    def load(self):
        self.driver.get(SUDOKU_HELPER_INDEX)
        if not self._page_ready(timeout=10):
            self.driver.get(SUDOKU_HELPER_PRETTY)
            if not self._page_ready(timeout=15):
                raise AssertionError(
                    "Sudoku Helper page did not load on /index.php/sudoku-helper/ or /sudoku-helper/"
                )
        return self

    def refresh(self):
        self.driver.refresh()
        if not self._page_ready(timeout=15):
            raise AssertionError("Sudoku Helper page did not finish loading after refresh.")
        return self

    def _page_ready(self, timeout: int) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(self.ROOT))
            WebDriverWait(self.driver, timeout).until(
                lambda d: len(d.find_elements(*self.CELLS)) == 81
            )
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(self.LOAD_BUTTON)
            )
            return True
        except TimeoutException:
            return False

    def wait_for_status_contains(self, text: str, timeout: int = 8):
        target = (text or "").strip().lower()
        WebDriverWait(self.driver, timeout).until(
            lambda d: target in ((d.find_element(*self.STATUS).text or "").strip().lower())
        )
        return self

    def status_text(self) -> str:
        return (self.driver.find_element(*self.STATUS).text or "").strip()

    def cell_count(self) -> int:
        return len(self.driver.find_elements(*self.CELLS))

    def _cell_locator(self, row: int, col: int):
        if not (1 <= row <= 9 and 1 <= col <= 9):
            raise ValueError("row and col must be between 1 and 9")
        return (
            By.CSS_SELECTOR,
            f".pd-sudoku__cell[data-row='{row - 1}'][data-col='{col - 1}']",
        )

    def cell_element(self, row: int, col: int):
        return self.driver.find_element(*self._cell_locator(row, col))

    def cell_input(self, row: int, col: int):
        return self.cell_element(row, col).find_element(By.CSS_SELECTOR, ".pd-sudoku__input")

    def click_cell(self, row: int, col: int):
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self._cell_locator(row, col))).click()
        return self

    def click_numpad(self, number: int):
        if not (1 <= int(number) <= 9):
            raise ValueError("number must be between 1 and 9")
        locator = (By.CSS_SELECTOR, f".pd-sudoku [data-number='{int(number)}']")
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(locator)).click()
        return self

    def cell_value(self, row: int, col: int) -> str:
        return (self.cell_input(row, col).get_attribute("value") or "").strip()

    def cell_is_locked(self, row: int, col: int) -> bool:
        classes = self.cell_element(row, col).get_attribute("class") or ""
        return "is-locked" in classes.split()

    def filled_count(self) -> int:
        count = 0
        for cell in self.driver.find_elements(*self.CELLS):
            try:
                value = (
                    cell.find_element(By.CSS_SELECTOR, ".pd-sudoku__input").get_attribute("value") or ""
                ).strip()
            except Exception:
                value = ""
            if value:
                count += 1
        return count

    def locked_count(self) -> int:
        count = 0
        for cell in self.driver.find_elements(*self.CELLS):
            classes = cell.get_attribute("class") or ""
            if "is-locked" in classes.split():
                count += 1
        return count

    def click_generate(self):
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.GENERATE_BUTTON)).click()
        return self

    def wait_for_generated(self, timeout: int = 45):
        end = time.time() + timeout
        while time.time() < end:
            filled = self.filled_count()
            locked = self.locked_count()
            if filled > 0 and locked > 0:
                return self
            time.sleep(0.2)
        raise AssertionError("Generate puzzle did not populate/lock any cells in time.")

    def load_button_element(self):
        return self.driver.find_element(*self.LOAD_BUTTON)

    def click_load(self):
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.LOAD_BUTTON)).click()
        return self

    def load_button_text(self) -> str:
        return (self.load_button_element().text or "").strip()

    def load_button_is_pending(self) -> bool:
        button = self.load_button_element()
        classes = (button.get_attribute("class") or "").split()
        busy = (button.get_attribute("aria-busy") or "").strip().lower() == "true"
        return ("is-pending" in classes) or busy

    def upload_save_file(self, path: str):
        abs_path = os.path.abspath(path)
        self.driver.find_element(*self.FILE_INPUT).send_keys(abs_path)
        return self

    def puzzle_name_value(self) -> str:
        return (self.driver.find_element(*self.NAME_INPUT).get_attribute("value") or "").strip()

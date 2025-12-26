from __future__ import annotations

from typing import Iterable

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from framework.urls import WP_ADMIN


class WpAdminTodoPage:
    URL = f"{WP_ADMIN.rstrip('/')}/admin.php?page=pd-todo"

    TABLE = (By.CSS_SELECTOR, "table.wp-list-table")
    ROWS = (By.CSS_SELECTOR, "table.wp-list-table tbody tr")
    NO_ITEMS = (By.CSS_SELECTOR, "table.wp-list-table .no-items")

    SEARCH_INPUT = (By.ID, "search-input")
    SEARCH_SUBMIT = (By.ID, "search-submit")
    SEARCH_FALLBACK = (By.NAME, "s")
    SEARCH_GENERIC = (By.CSS_SELECTOR, "form.search-box input[type='search'], form.search-box input[type='text']")

    BULK_SELECT_TOP = (By.ID, "bulk-action-selector-top")
    BULK_APPLY_TOP = (By.ID, "doaction")
    NOTICE = (By.CSS_SELECTOR, "div.notice, div.updated, div.error")

    TITLE_IN_ROW = (By.CSS_SELECTOR, "td.column-title strong")
    STATUS_IN_ROW = (By.CSS_SELECTOR, "td.column-status")
    ROW_CHECKBOX = (By.CSS_SELECTOR, "th.check-column input[type='checkbox'][name='ids[]']")

    def __init__(self, driver):
        self.driver = driver

    def open(self):
        self.driver.get(self.URL)
        WebDriverWait(self.driver, 25).until(EC.presence_of_element_located(self.TABLE))
        return self

    def _table_snapshot(self) -> tuple[int, str]:
        rows = self.driver.find_elements(*self.ROWS)
        if not rows:
            empty = self.driver.find_elements(*self.NO_ITEMS)
            txt = (empty[0].text or "").strip() if empty else ""
            return (0, txt)
        return (len(rows), rows[0].text.strip())

    def search(self, query: str):
        table = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(self.TABLE))
        before = self._table_snapshot()

        locators = [self.SEARCH_INPUT, self.SEARCH_FALLBACK, self.SEARCH_GENERIC]
        inp = None
        for loc in locators:
            found = self.driver.find_elements(*loc)
            if found:
                inp = found[0]
                break

        if not inp:
            # No search box on this screen; rely on existing rows.
            return self

        inp.clear()
        inp.send_keys(query)

        submits = self.driver.find_elements(*self.SEARCH_SUBMIT)
        if submits:
            submits[0].click()
        else:
            inp.submit()

        def changed(_):
            try:
                return EC.staleness_of(table)(_) or self._table_snapshot() != before
            except StaleElementReferenceException:
                return True

        WebDriverWait(self.driver, 20).until(changed)
        return self

    def _rows_by_title(self, titles: Iterable[str]) -> dict[str, WebElement]:
        wanted = {t.strip() for t in titles}
        found: dict[str, WebElement] = {}
        for row in self.driver.find_elements(*self.ROWS):
            title_cells = row.find_elements(*self.TITLE_IN_ROW)
            if not title_cells:
                continue
            text = (title_cells[0].text or "").strip()
            if text in wanted:
                found[text] = row
        return found

    def select_rows_by_title(self, titles: Iterable[str]):
        titles_set = {t.strip() for t in titles}
        found = self._rows_by_title(titles_set)
        missing = titles_set - set(found.keys())
        assert not missing, f"Could not find rows with title(s): {sorted(missing)}"

        for row in found.values():
            cb = row.find_element(*self.ROW_CHECKBOX)
            if not cb.is_selected():
                cb.click()
        return self

    def apply_bulk_action(self, action_value: str):
        table = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(self.TABLE))
        before = self._table_snapshot()

        Select(self.driver.find_element(*self.BULK_SELECT_TOP)).select_by_value(action_value)
        self.driver.find_element(*self.BULK_APPLY_TOP).click()

        def finished(_):
            try:
                if EC.staleness_of(table)(_) or self._table_snapshot() != before:
                    return True
                notices = self.driver.find_elements(*self.NOTICE)
                for n in notices:
                    txt = (n.text or "").lower()
                    if "updated" in txt or "error" in txt or "deleted" in txt or "added" in txt or "status" in txt:
                        return True
                return False
            except StaleElementReferenceException:
                return True

        WebDriverWait(self.driver, 25).until(finished)
        return self

    def status_for_title(self, title: str) -> str:
        rows = self._rows_by_title([title])
        assert title in rows, f"Row with title {title!r} not found."
        status_cells = rows[title].find_elements(*self.STATUS_IN_ROW)
        return (status_cells[0].text or "").strip() if status_cells else ""

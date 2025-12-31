from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from framework.urls import WP_ADMIN


class WpAdminSwlHistoryPage:
    URL_HISTORY = f"{WP_ADMIN.rstrip('/')}/admin.php?page=pdswl-history"
    URL_LEGACY = f"{WP_ADMIN.rstrip('/')}/admin.php?page=pdswl-entries"

    TABLE = (By.CSS_SELECTOR, "table.widefat")
    ROWS = (By.CSS_SELECTOR, "table.widefat tbody tr")
    NOTICE = (By.CSS_SELECTOR, "div.notice, div.updated, div.error")

    def __init__(self, driver):
        self.driver = driver

    def open(self):
        """
        Open the read-only Workout History page (new slug), falling back to the legacy slug if needed.
        """
        self._go(self.URL_HISTORY)
        if not self._table_present(timeout=10):
            self._go(self.URL_LEGACY)
            self._table_present(timeout=10)
        return self

    def row_count(self) -> int:
        return len(self.driver.find_elements(*self.ROWS))

    def rows_text(self) -> list[str]:
        rows = []
        for row in self.driver.find_elements(*self.ROWS):
            txt = (row.text or "").strip()
            if txt:
                rows.append(txt)
        return rows

    def notice_text(self) -> str:
        notices = self.driver.find_elements(*self.NOTICE)
        return " ".join((n.text or "").strip() for n in notices if (n.text or "").strip())

    def _go(self, url: str):
        self.driver.get(url)

    def _table_present(self, timeout: int = 15) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(self.TABLE))
            return True
        except Exception:
            return False


# Backward-compatible alias for older test imports.
WpAdminSwlEntriesPage = WpAdminSwlHistoryPage

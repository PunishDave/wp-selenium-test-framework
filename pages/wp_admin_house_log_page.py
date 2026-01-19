from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from framework.urls import WP_ADMIN


class WpAdminHouseLogPage:
    URL = f"{WP_ADMIN.rstrip('/')}/admin.php?page=pd-house-log"

    TABLE = (By.CSS_SELECTOR, "table.widefat")
    ROWS = (By.CSS_SELECTOR, "table.widefat tbody tr")
    NOTICE = (By.CSS_SELECTOR, ".notice-success, .notice-error, .updated, .error")

    def __init__(self, driver):
        self.driver = driver

    def open(self):
        self.driver.get(self.URL)
        self.wait_loaded()
        return self

    def wait_loaded(self, timeout: int = 20):
        WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(self.TABLE))
        return self

    def _rows(self):
        return self.driver.find_elements(*self.ROWS)

    def row_titles(self) -> list[str]:
        titles: list[str] = []
        for row in self._rows():
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue
            title = (cells[0].text or "").strip()
            if title and "No issues" not in title:
                titles.append(title)
        return titles

    def _row_for_title(self, title: str):
        for row in self._rows():
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue
            text = (cells[0].text or "").strip()
            if text.lower() == title.lower():
                return row
        return None

    def has_title(self, title: str) -> bool:
        return any(t.lower() == title.lower() for t in self.row_titles())

    def get_issue_id(self, title: str) -> int:
        row = self._row_for_title(title)
        if not row:
            raise AssertionError(f"Issue titled '{title}' not found in admin list.")

        links = row.find_elements(By.TAG_NAME, "a")
        for link in links:
            if (link.text or "").strip().lower() == "edit":
                href = link.get_attribute("href") or ""
                query = parse_qs(urlparse(href).query)
                issue_id = query.get("id", [""])[0]
                return int(issue_id) if issue_id.isdigit() else 0

        raise AssertionError("Edit link not found for issue row.")

    def delete_issue(self, title: str):
        row = self._row_for_title(title)
        if not row:
            raise AssertionError(f"Issue titled '{title}' not found in admin list.")

        links = row.find_elements(By.TAG_NAME, "a")
        delete_link = None
        for link in links:
            if (link.text or "").strip().lower() == "delete":
                delete_link = link
                break

        if not delete_link:
            raise AssertionError("Delete link not found for issue row.")

        delete_link.click()
        try:
            alert = self.driver.switch_to.alert
            alert.accept()
        except Exception:
            pass

        def removed(_):
            return not self.has_title(title)

        WebDriverWait(self.driver, 12).until(removed)
        return self

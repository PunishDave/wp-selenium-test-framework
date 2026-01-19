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
    SECTION_ACTIVE = "Active Issues"
    SECTION_COMPLETED = "Completed Issues"

    def __init__(self, driver):
        self.driver = driver

    def open(self):
        self.driver.get(self.URL)
        self.wait_loaded()
        return self

    def wait_loaded(self, timeout: int = 20):
        WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(self.TABLE))
        return self

    def _table_for_section(self, section: str):
        heading = self.driver.find_element(By.XPATH, f"//h2[normalize-space()='{section}']")
        return heading.find_element(By.XPATH, "following-sibling::table[1]")

    def _rows(self, section: str | None = None):
        if section:
            table = self._table_for_section(section)
            return table.find_elements(By.CSS_SELECTOR, "tbody tr")
        return self.driver.find_elements(*self.ROWS)

    def row_titles(self, section: str | None = None) -> list[str]:
        titles: list[str] = []
        for row in self._rows(section):
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue
            title = (cells[0].text or "").strip()
            if title and not title.lower().startswith("no "):
                titles.append(title)
        return titles

    def _row_for_title(self, title: str, section: str | None = None):
        for row in self._rows(section):
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue
            text = (cells[0].text or "").strip()
            if text.lower() == title.lower():
                return row
        return None

    def has_title(self, title: str, section: str | None = None) -> bool:
        return any(t.lower() == title.lower() for t in self.row_titles(section))

    def get_issue_id(self, title: str, section: str | None = None) -> int:
        row = self._row_for_title(title, section)
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

    def _find_action_link(self, row, label: str):
        for link in row.find_elements(By.TAG_NAME, "a"):
            if (link.text or "").strip().lower() == label.lower():
                return link
        return None

    def delete_issue(self, title: str, section: str | None = None):
        row = self._row_for_title(title, section)
        if not row:
            raise AssertionError(f"Issue titled '{title}' not found in admin list.")

        delete_link = self._find_action_link(row, "Delete")
        if not delete_link:
            raise AssertionError("Delete link not found for issue row.")

        delete_link.click()
        try:
            alert = self.driver.switch_to.alert
            alert.accept()
        except Exception:
            pass

        def removed(_):
            return not self.has_title(title, section)

        WebDriverWait(self.driver, 12).until(removed)
        return self

    def mark_completed(self, title: str):
        row = self._row_for_title(title, self.SECTION_ACTIVE)
        if not row:
            raise AssertionError(f"Issue titled '{title}' not found in active list.")

        complete_link = self._find_action_link(row, "Mark completed")
        if not complete_link:
            raise AssertionError("Mark completed link not found for issue row.")

        complete_link.click()

        def moved(_):
            return not self.has_title(title, self.SECTION_ACTIVE) and self.has_title(title, self.SECTION_COMPLETED)

        WebDriverWait(self.driver, 12).until(moved)
        return self

    def reopen_issue(self, title: str):
        row = self._row_for_title(title, self.SECTION_COMPLETED)
        if not row:
            raise AssertionError(f"Issue titled '{title}' not found in completed list.")

        reopen_link = self._find_action_link(row, "Reopen")
        if not reopen_link:
            raise AssertionError("Reopen link not found for issue row.")

        reopen_link.click()

        def moved(_):
            return self.has_title(title, self.SECTION_ACTIVE) and not self.has_title(title, self.SECTION_COMPLETED)

        WebDriverWait(self.driver, 12).until(moved)
        return self

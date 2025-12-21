# pages/have_we_got_import_admin_page.py

from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from framework.urls import WP_ADMIN


class HaveWeGotImportAdminPage:
    """
    WP Admin page: Have We Got - Import
    Direct URL (stable): http://localhost/wp-admin/admin.php?page=have-we-got
    """

    PAGE_SLUG = "admin.php?page=have-we-got"

    # Page title
    H1_IMPORT = (By.XPATH, "//h1[normalize-space()='Have We Got - Import']")

    # Upload + submit
    FILE_INPUT = (By.ID, "have_we_got_xml")      # <input type="file" ...>
    IMPORT_SUBMIT = (By.ID, "submit")            # <input type="submit" id="submit" ...>

    def __init__(self, driver):
        self.driver = driver

    def open(self):
        url = f"{WP_ADMIN.rstrip('/')}/{self.PAGE_SLUG}"
        self.driver.get(url)
        WebDriverWait(self.driver, 25).until(EC.presence_of_element_located(self.H1_IMPORT))
        return self

    def upload_file(self, xml_path: str):
        WebDriverWait(self.driver, 25).until(EC.presence_of_element_located(self.FILE_INPUT))
        self.driver.find_element(*self.FILE_INPUT).send_keys(xml_path)
        return self

    def click_import(self):
        WebDriverWait(self.driver, 25).until(EC.element_to_be_clickable(self.IMPORT_SUBMIT)).click()
        return self

    def upload_and_import(self, xml_path: str):
        return self.upload_file(xml_path).click_import()

    def wait_for_import_success(self, added: int = 4, updated: int = 0):
        msg = f"Import complete. {added} added, {updated} updated."
        return self.wait_for_text(msg)

    def wait_for_parse_error(self):
        return self.wait_for_text("Could not parse XML file.")

    def wait_for_text(self, text: str, timeout: int = 30):
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, f"//*[contains(normalize-space(.), {self._xpath_literal(text)})]"))
        )
        return self

    @staticmethod
    def _xpath_literal(s: str) -> str:
        # Safe XPath string literal helper
        if "'" not in s:
            return f"'{s}'"
        if '"' not in s:
            return f'"{s}"'
        parts = s.split("'")
        return "concat(" + ", \"'\", ".join([f"'{p}'" for p in parts]) + ")"


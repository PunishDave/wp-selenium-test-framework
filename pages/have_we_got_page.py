import re
from dataclasses import dataclass
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

from framework.urls import HAVEWEGOT


@dataclass(frozen=True)
class HaveWeGotRow:
    type: str
    name: str
    status: str
    last_access: str


class HaveWeGotPage:
    URL = HAVEWEGOT

    # Filters
    TYPE = (By.NAME, "hwg_type")
    STATUS = (By.NAME, "hwg_status")
    SEARCH = (By.NAME, "hwg_search")
    ORDER = (By.NAME, "hwg_order")
    FILTER_SUBMIT = (By.CSS_SELECTOR, "form button[type='submit'], form input[type='submit']")

    # Table
    TABLE = (By.CSS_SELECTOR, ".have-we-got__table")
    HEADER_CELLS = (By.CSS_SELECTOR, ".have-we-got__table thead th")
    ROWS = (By.CSS_SELECTOR, ".have-we-got__table tbody tr")

    # “No results” patterns (covers common WP / DataTables patterns)
    NO_RESULTS = (
        By.XPATH,
        "//*[contains(translate(., 'NORESULTS', 'noresults'), 'no results') "
        "or contains(translate(., 'NOMATCHINGRECORDS', 'nomatchingrecords'), 'no matching records') "
        "or contains(translate(., 'NOTHINGFOUND', 'nothingfound'), 'nothing found') "
        "or contains(translate(., 'NOENTRIES', 'noentries'), 'no entries')]",
    )

    def __init__(self, driver):
        self.driver = driver

    def load(self):
        self.driver.get(self.URL)
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(self.SEARCH))
        return self

    # ---------- Presence helpers ----------

    def _has_table(self) -> bool:
        return len(self.driver.find_elements(*self.TABLE)) > 0

    def _has_no_results_message(self) -> bool:
        return len(self.driver.find_elements(*self.NO_RESULTS)) > 0

    def _wait_for_results_area(self):
        """
        Wait until either:
        - the results table exists, OR
        - a 'no results' message exists
        """
        def ready(_):
            return self._has_table() or self._has_no_results_message()

        WebDriverWait(self.driver, 25).until(ready)

    # ---------- Filters ----------

    def set_type(self, visible_text: str):
        Select(self.driver.find_element(*self.TYPE)).select_by_visible_text(visible_text)

    def set_order(self, visible_text: str):
        Select(self.driver.find_element(*self.ORDER)).select_by_visible_text(visible_text)

    def set_status(self, value: str):
        el = self.driver.find_element(*self.STATUS)
        el.clear()
        el.send_keys(value)

    def set_search(self, value: str):
        el = self.driver.find_element(*self.SEARCH)
        el.clear()
        el.send_keys(value)

    # ---------- Snapshot / waiting ----------

    def _table_snapshot(self) -> tuple[int, str]:
        """
        Returns a stable snapshot:
        - (0, '') if no table or no rows
        - otherwise (row_count, first_row_text)
        """
        self._wait_for_results_area()

        if not self._has_table():
            return (0, "")

        rows = self.driver.find_elements(*self.ROWS)
        if not rows:
            return (0, "")
        return (len(rows), rows[0].text.strip())

    def submit_filters(self):
        """
        Click submit and wait for *some* observable change:
        - URL change (GET params), OR
        - results snapshot change, OR
        - no-results message appears
        """
        before_url = self.driver.current_url
        before = self._table_snapshot()

        self.driver.find_element(*self.FILTER_SUBMIT).click()

        def changed(_):
            try:
                # URL change is a strong signal in WP filter forms
                if self.driver.current_url != before_url:
                    return True

                # No-results appearing is also valid
                if self._has_no_results_message():
                    return True

                # Otherwise compare table snapshot
                return self._table_snapshot() != before
            except StaleElementReferenceException:
                return False

        WebDriverWait(self.driver, 25).until(changed)

    # ---------- Reading results ----------

    def read_rows(self) -> list[HaveWeGotRow]:
        self._wait_for_results_area()

        # If there is no table, treat as "no rows"
        if not self._has_table():
            return []

        out: list[HaveWeGotRow] = []
        for tr in self.driver.find_elements(*self.ROWS):
            tds = tr.find_elements(By.CSS_SELECTOR, "td")
            if len(tds) < 4:
                continue
            out.append(
                HaveWeGotRow(
                    type=tds[0].text.strip(),
                    name=tds[1].text.strip(),
                    status=tds[2].text.strip(),
                    last_access=tds[3].text.strip(),
                )
            )
        return out

    # ---------- Headers / sorting ----------

    def header_texts(self) -> list[str]:
        self._wait_for_results_area()
        if not self._has_table():
            return []

        cleaned: list[str] = []
        for h in self.driver.find_elements(*self.HEADER_CELLS):
            first_line = (h.text or "").strip().splitlines()[0].strip()
            first_line = re.sub(r"[↑↓⇅⇧⇩]", "", first_line).strip()
            first_line = re.sub(r"\s+", " ", first_line).strip()
            cleaned.append(first_line)
        return cleaned

    def click_header(self, header_name: str):
        self._wait_for_results_area()
        if not self._has_table():
            raise AssertionError("Cannot sort headers: results table is not present.")

        target = header_name.strip().lower()

        def sort_state(th):
            # Prefer aria-sort if present; fall back to class name
            aria = (th.get_attribute("aria-sort") or "").strip().lower()
            cls = (th.get_attribute("class") or "").strip().lower()
            return aria or cls

        ths = self.driver.find_elements(*self.HEADER_CELLS)
        for th in ths:
            label = (th.text or "").strip().splitlines()[0].strip()
            label = re.sub(r"[↑↓⇅⇧⇩]", "", label).strip().lower()

            if label == target:
                before_state = sort_state(th)
                th.click()

                def changed(_):
                    try:
                        # State changed is the best signal for a sort click
                        now_state = sort_state(th)
                        if now_state and now_state != before_state:
                            return True
                        # fallback: table content changed
                        return self._table_snapshot() != (0, "")  # forces a refresh check without assuming ordering changes
                    except StaleElementReferenceException:
                        return False

                WebDriverWait(self.driver, 25).until(changed)
                return

        found = [(t.text or "").strip().splitlines()[0].strip() for t in ths]
        raise AssertionError(f"Header '{header_name}' not found. Found headers: {found}")



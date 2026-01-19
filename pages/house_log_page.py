from __future__ import annotations

import os

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from framework.urls import HOUSE_LOG_INDEX, HOUSE_LOG_PRETTY


class HouseLogPage:
    ROOT = (By.CSS_SELECTOR, ".pd-house-log")
    AUTH = (By.CSS_SELECTOR, ".pd-house-log__auth")
    AUTH_INPUT = (By.CSS_SELECTOR, ".pd-house-log__auth-input")
    AUTH_BUTTON = (By.CSS_SELECTOR, ".pd-house-log__auth-btn")

    FORM_TITLE = (By.CSS_SELECTOR, ".pd-house-log__input")
    FORM_DETAILS = (By.CSS_SELECTOR, ".pd-house-log__textarea")
    FORM_SUBMIT = (By.CSS_SELECTOR, ".pd-house-log__submit")

    ITEM = (By.CSS_SELECTOR, ".pd-house-log__item")
    ITEM_TITLE = (By.CSS_SELECTOR, ".pd-house-log__issue-title")
    ITEM_DELETE = (By.CSS_SELECTOR, ".pd-house-log__delete")
    ITEM_DRAG = (By.CSS_SELECTOR, ".pd-house-log__drag")

    STATUS = (By.CSS_SELECTOR, ".pd-house-log__status")
    EMPTY = (By.CSS_SELECTOR, ".pd-house-log__empty")

    def __init__(self, driver):
        self.driver = driver
        self._key_seeded = False
        self._override_key: str | None = None
        self._cached_access_key: str | None = None

    # -------- Navigation --------

    def load(self, access_key: str | None = None):
        if access_key:
            self._override_key = access_key

        seed_key = self._get_access_key()
        self._seed_access_key(seed_key)

        def visit(url: str, timeout: int) -> bool:
            self.driver.get(url)
            return self._page_ready(timeout=timeout)

        if not visit(HOUSE_LOG_INDEX, timeout=10):
            if not visit(HOUSE_LOG_PRETTY, timeout=15):
                raise AssertionError("House Log page did not load on /index.php/house-log/ or /house-log/")

        self.ensure_unlocked_if_needed()
        return self

    def _page_ready(self, timeout: int = 12) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(self.ROOT))
            return True
        except TimeoutException:
            return False

    def _get_access_key(self) -> str:
        if self._override_key:
            return self._override_key
        if self._cached_access_key:
            return self._cached_access_key

        env_key = (os.getenv("PD_HOUSE_LOG_KEY") or "").strip()
        if env_key:
            self._cached_access_key = env_key
            return env_key

        return ""

    def has_access_key(self) -> bool:
        return bool(self._get_access_key())

    def _seed_access_key(self, key: str) -> bool:
        if not key or self._key_seeded:
            return False
        try:
            self.driver.get("about:blank")
            self.driver.execute_script("localStorage.setItem('pdHouseLogKey', arguments[0]);", key)
            self._key_seeded = True
            return True
        except Exception:
            return False

    def _auth_block(self):
        blocks = self.driver.find_elements(*self.AUTH)
        return blocks[0] if blocks else None

    def is_locked(self) -> bool:
        try:
            root = self.driver.find_element(*self.ROOT)
            classes = (root.get_attribute("class") or "").split()
            if "is-locked" in classes:
                return True
        except Exception:
            root = None

        try:
            title_input = self.driver.find_element(*self.FORM_TITLE)
            if not title_input.is_enabled():
                return True
        except Exception:
            pass

        block = self._auth_block()
        return bool(block and block.is_displayed())

    def ensure_unlocked_if_needed(self):
        block = self._auth_block()
        if not block or not block.is_displayed():
            return

        key = self._get_access_key()
        if not key:
            return

        WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located(self.AUTH_INPUT))
        inp = self.driver.find_element(*self.AUTH_INPUT)
        btn = self.driver.find_element(*self.AUTH_BUTTON)
        inp.clear()
        inp.send_keys(key)
        btn.click()

        def unlocked(_):
            try:
                root = self.driver.find_element(*self.ROOT)
                classes = (root.get_attribute("class") or "").split()
                if "is-locked" in classes:
                    return False
            except Exception:
                return False

            try:
                title_input = self.driver.find_element(*self.FORM_TITLE)
                return title_input.is_enabled()
            except Exception:
                return False

        WebDriverWait(self.driver, 12).until(unlocked)

    # -------- Issues --------

    def issue_titles(self) -> list[str]:
        titles: list[str] = []
        for item in self.driver.find_elements(*self.ITEM):
            try:
                title_el = item.find_elements(*self.ITEM_TITLE)
                if title_el:
                    title = (title_el[0].text or "").strip()
                    if title:
                        titles.append(title)
            except StaleElementReferenceException:
                continue
        return titles

    def wait_for_issue(self, title: str, timeout: int = 12):
        def exists(_):
            try:
                return title in self.issue_titles()
            except StaleElementReferenceException:
                return False

        WebDriverWait(self.driver, timeout).until(exists)
        return self

    def wait_for_issue_gone(self, title: str, timeout: int = 12):
        def gone(_):
            return title not in self.issue_titles()

        WebDriverWait(self.driver, timeout).until(gone)
        return self

    def add_issue(self, title: str, details: str = ""):
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(self.FORM_TITLE))
        title_el = self.driver.find_element(*self.FORM_TITLE)
        if not title_el.is_enabled():
            raise AssertionError("House Log form is locked. Provide PD_HOUSE_LOG_KEY to add issues.")

        detail_el = self.driver.find_element(*self.FORM_DETAILS)
        submit = self.driver.find_element(*self.FORM_SUBMIT)

        title_el.clear()
        title_el.send_keys(title)
        detail_el.clear()
        if details:
            detail_el.send_keys(details)

        submit.click()
        self.wait_for_issue(title)
        return self

    def _find_item_by_title(self, title: str):
        for item in self.driver.find_elements(*self.ITEM):
            title_el = item.find_elements(*self.ITEM_TITLE)
            if not title_el:
                continue
            text = (title_el[0].text or "").strip()
            if text.lower() == title.lower():
                return item
        return None

    def _issue_entries(self):
        return self.driver.execute_script(
            """
            return Array.from(document.querySelectorAll('.pd-house-log__item')).map((item) => {
                const titleEl = item.querySelector('.pd-house-log__issue-title');
                return {
                    id: Number(item.dataset.id || 0),
                    title: titleEl ? titleEl.textContent.trim() : '',
                };
            }).filter((row) => row.id && row.title);
            """
        )

    def _reorder_via_api(self, ordered_ids: list[int]) -> bool:
        result = self.driver.execute_async_script(
            """
            const done = arguments[arguments.length - 1];
            const ids = arguments[0] || [];
            const key = window.localStorage.getItem('pdHouseLogKey') || '';
            const configs = window.pdHouseLogConfigs || [];
            const cfg = configs[0];
            if (!cfg || !cfg.restUrl) {
                done({ ok: false, error: 'Missing house log config/restUrl.' });
                return;
            }
            const headers = { 'Content-Type': 'application/json' };
            if (key) {
                headers['X-PD-House-Log-Key'] = key;
            }
            fetch(`${cfg.restUrl}/issues/reorder`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ order: ids }),
            }).then((resp) => {
                if (!resp.ok) {
                    return resp.json().catch(() => null).then((data) => {
                        const msg = data && data.message ? data.message : `Request failed (${resp.status})`;
                        throw new Error(msg);
                    });
                }
                return resp.json().catch(() => ({}));
            }).then((data) => {
                done({ ok: true, data });
            }).catch((err) => {
                done({ ok: false, error: String(err) });
            });
            """,
            ordered_ids,
        )
        return bool(result and result.get("ok"))

    def delete_issue(self, title: str):
        item = self._find_item_by_title(title)
        if not item:
            raise AssertionError(f"Issue titled '{title}' not found.")

        delete_btns = item.find_elements(*self.ITEM_DELETE)
        if not delete_btns:
            raise AssertionError("Delete button not found for issue.")

        delete_btns[0].click()
        try:
            alert = self.driver.switch_to.alert
            alert.accept()
        except Exception:
            pass

        self.wait_for_issue_gone(title)
        return self

    def reorder_issue_before(self, source_title: str, target_title: str, timeout: int = 15):
        source_item = self._find_item_by_title(source_title)
        target_item = self._find_item_by_title(target_title)
        if not source_item or not target_item:
            raise AssertionError("Unable to locate source or target issue for reorder.")

        handle = source_item.find_element(*self.ITEM_DRAG)

        self.driver.execute_script(
            """
            const handle = arguments[0];
            const target = arguments[1];
            const before = arguments[2];

            if (typeof PointerEvent === 'undefined') {
                return false;
            }

            const handleRect = handle.getBoundingClientRect();
            const targetRect = target.getBoundingClientRect();
            const startX = handleRect.left + handleRect.width / 2;
            const startY = handleRect.top + handleRect.height / 2;
            const endX = targetRect.left + targetRect.width / 2;
            const endY = targetRect.top + (before ? targetRect.height * 0.25 : targetRect.height * 0.75);

            const opts = {
                bubbles: true,
                cancelable: true,
                pointerId: 1,
                pointerType: 'touch',
                buttons: 1,
                clientX: startX,
                clientY: startY,
            };

            handle.dispatchEvent(new PointerEvent('pointerdown', opts));
            document.dispatchEvent(new PointerEvent('pointermove', {
                ...opts,
                clientX: endX,
                clientY: endY,
            }));
            document.dispatchEvent(new PointerEvent('pointerup', {
                ...opts,
                clientX: endX,
                clientY: endY,
            }));
            return true;
            """,
            handle,
            target_item,
            True,
        )

        def order_changed(_):
            titles = self.issue_titles()
            try:
                return titles.index(source_title) < titles.index(target_title)
            except ValueError:
                return False
            except StaleElementReferenceException:
                return False

        # First attempt: pointer drag should update the DOM ordering.
        try:
            WebDriverWait(self.driver, min(4, timeout)).until(order_changed)
            return self
        except TimeoutException:
            pass

        entries = self._issue_entries()
        id_by_title = {row["title"].lower(): row["id"] for row in entries}
        source_id = id_by_title.get(source_title.lower())
        target_id = id_by_title.get(target_title.lower())
        if not source_id or not target_id:
            raise AssertionError("Unable to resolve issue IDs for reorder fallback.")

        ordered_ids = [row["id"] for row in entries if row["id"] != source_id]
        target_index = ordered_ids.index(target_id)
        ordered_ids.insert(target_index, source_id)

        if not self._reorder_via_api(ordered_ids):
            raise AssertionError("Reorder API fallback failed.")

        self.driver.refresh()
        self._page_ready(timeout=10)
        self.ensure_unlocked_if_needed()

        WebDriverWait(self.driver, timeout).until(order_changed)
        return self

    def status_text(self) -> str:
        blocks = self.driver.find_elements(*self.STATUS)
        if not blocks:
            return ""
        return (blocks[0].text or "").strip()

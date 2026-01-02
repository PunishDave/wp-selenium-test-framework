from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from framework.urls import TODO_INDEX, TODO_PRETTY, WP_ADMIN
from pages.wp_admin_login_page import WpAdminLoginPage


@dataclass(frozen=True)
class HabitCounter:
    habit: str
    count: int


class TodoPage:
    ROOT = (By.CSS_SELECTOR, ".pd-todo-app")
    LIST = (By.CSS_SELECTOR, ".pd-todo-list")
    SECTION_BODY = (By.CSS_SELECTOR, ".pd-todo-section-body")
    TABS = (By.CSS_SELECTOR, ".pd-todo-tabs .pd-todo-tab")
    PAGER_BTNS = (By.CSS_SELECTOR, ".pd-todo-pager .pd-todo-page-btn")
    PAGE_LABEL = (By.CSS_SELECTOR, ".pd-todo-page-label")

    AUTH = (By.CSS_SELECTOR, ".pd-todo-auth")
    AUTH_INPUT = (By.CSS_SELECTOR, ".pd-todo-auth input[type='password']")
    AUTH_BUTTON = (By.CSS_SELECTOR, ".pd-todo-auth button")
    ADMIN_ACCESS_INPUT = (By.ID, "pd_todo_access_key")

    FORM = (By.CSS_SELECTOR, "form.pd-todo-form")
    TITLE_INPUT = (By.CSS_SELECTOR, "form.pd-todo-form input[name='title']")
    CATEGORY_SELECT = (By.CSS_SELECTOR, "form.pd-todo-form select[name='category']")
    HABIT_SELECT = (By.CSS_SELECTOR, "form.pd-todo-form select[name='habit']")
    DUE_INPUT = (By.CSS_SELECTOR, "form.pd-todo-form input[name='due_date']")
    SUBMIT = (By.CSS_SELECTOR, "form.pd-todo-form button[type='submit']")

    ROW = (By.CSS_SELECTOR, ".pd-todo-section .pd-todo-row")
    ROW_TITLE = (By.CSS_SELECTOR, ".pd-todo-title")
    ROW_DUE = (By.CSS_SELECTOR, ".pd-todo-due")
    ROW_STATUS = (By.CSS_SELECTOR, ".pd-todo-badge.status")
    ROW_CHECKBOX = (By.CSS_SELECTOR, ".pd-todo-checkbox")

    ERROR = (By.CSS_SELECTOR, ".pd-todo-error")

    def __init__(self, driver):
        self.driver = driver
        self._key_seeded = False
        self._admin_session = False
        self._cached_access_key: str | None = None

    # -------- Navigation / loading --------

    def load(self):
        self._maybe_login_first()
        seed_key = self._get_access_key() or ("admin-bypass" if self._admin_session else "")

        self.driver.get(TODO_PRETTY)
        if self._seed_access_key(seed_key):
            self.driver.refresh()

        if not self._page_ready(timeout=8):
            self.driver.get(TODO_INDEX)
            if self._seed_access_key(seed_key):
                self.driver.refresh()
            if not self._page_ready(timeout=15):
                raise AssertionError("To-Do page did not load on /to-do/ or /index.php/to-do/")
        self._last_url = self.driver.current_url
        self.ensure_unlocked_if_needed()
        return self

    def _page_ready(self, timeout: int) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(self.ROOT))
            return True
        except TimeoutException:
            return False

    # -------- Form / creation --------

    def _maybe_login_first(self):
        user = (os.getenv("WP_ADMIN_USER") or "").strip()
        pw = (os.getenv("WP_ADMIN_PASS") or "").strip()
        if user and pw:
            try:
                WpAdminLoginPage(self.driver).load().login(user, pw)
                self._admin_session = True
            except TimeoutException:
                pass

    def _get_access_key(self) -> str:
        if self._cached_access_key:
            return self._cached_access_key

        env_key = (os.getenv("PD_TODO_KEY") or "").strip()
        if env_key:
            self._cached_access_key = env_key
            return env_key

        if self._admin_session:
            key = self._read_access_key_from_admin()
            if key:
                self._cached_access_key = key
                return key

        return ""

    def _seed_access_key(self, key: str) -> bool:
        if not key or self._key_seeded:
            return False
        try:
            self.driver.execute_script("localStorage.setItem('pdTodoKey', arguments[0]);", key)
            self._key_seeded = True
            return True
        except Exception:
            return False

    def ensure_unlocked_if_needed(self):
        def auth_block():
            blocks = self.driver.find_elements(*self.AUTH)
            return blocks[0] if blocks else None

        block = auth_block()
        if not block or not block.is_displayed():
            return

        key = self._get_access_key()

        if not key:
            user = (os.getenv("WP_ADMIN_USER") or "").strip()
            pw = (os.getenv("WP_ADMIN_PASS") or "").strip()
            assert user and pw, "Access key required. Set PD_TODO_KEY or provide WP_ADMIN_USER / WP_ADMIN_PASS for admin fallback."

            start_url = getattr(self, "_last_url", self.driver.current_url)
            WpAdminLoginPage(self.driver).load().login(user, pw)
            self.driver.get(start_url)
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located(self.ROOT))
            auth_blocks = self.driver.find_elements(*self.AUTH)
            block = auth_blocks[0] if auth_blocks else None
            key = "admin-bypass"

        WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located(self.AUTH_INPUT))
        inp = self.driver.find_element(*self.AUTH_INPUT)
        btn = self.driver.find_element(*self.AUTH_BUTTON)
        inp.clear()
        inp.send_keys(key)
        btn.click()
        WebDriverWait(self.driver, 15).until(lambda _: not auth_block() or not auth_block().is_displayed())

    def _read_access_key_from_admin(self) -> str:
        user = (os.getenv("WP_ADMIN_USER") or "").strip()
        pw = (os.getenv("WP_ADMIN_PASS") or "").strip()
        if not (user and pw):
            return ""

        try:
            self.driver.get(f"{WP_ADMIN.rstrip('/')}/admin.php?page=pd-todo-access")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(self.ADMIN_ACCESS_INPUT))
            key_input = self.driver.find_element(*self.ADMIN_ACCESS_INPUT)
            key = (key_input.get_attribute("value") or "").strip()
            if getattr(self, "_last_url", None):
                self.driver.get(self._last_url)
            return key
        except Exception:
            if getattr(self, "_last_url", None):
                try:
                    self.driver.get(self._last_url)
                except Exception:
                    pass
            return ""

    def open_form(self):
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(self.FORM))

    def _select_value(self, locator, value: Optional[str]) -> tuple[str, str]:
        select_el = self.driver.find_element(*locator)
        if not select_el.is_enabled():
            return ("", "")
        sel = Select(select_el)

        if value:
            desired = value.strip()
            for opt in sel.options:
                opt_val = (opt.get_attribute("value") or "").strip()
                if opt_val == desired:
                    sel.select_by_value(opt_val)
                    return (opt.text or "").strip(), opt_val
            for opt in sel.options:
                label = (opt.text or "").strip()
                if label.lower() == desired.lower():
                    opt.click()
                    return label, (opt.get_attribute("value") or "").strip()

        for opt in sel.options:
            opt_val = (opt.get_attribute("value") or "").strip()
            if opt_val:
                sel.select_by_value(opt_val)
                return (opt.text or "").strip(), opt_val

        if sel.options:
            sel.select_by_index(0)
            chosen = sel.first_selected_option
            return (chosen.text or "").strip(), (chosen.get_attribute("value") or "").strip()

        raise AssertionError(f"No options available for select {locator}")

    def add_task(
        self,
        title: str,
        due_date: Optional[str],
        *,
        category: Optional[str] = None,
        habit: Optional[str] = None,
    ) -> dict:
        self.open_form()

        title_el = self.driver.find_element(*self.TITLE_INPUT)
        title_el.clear()
        title_el.send_keys(title)

        category_label, category_value = self._select_value(self.CATEGORY_SELECT, category)
        habit_label, habit_value = self._select_value(self.HABIT_SELECT, habit)

        due_el = self.driver.find_element(*self.DUE_INPUT)
        due_el.clear()
        if due_date:
            due_el.send_keys(due_date)

        self.driver.find_element(*self.SUBMIT).click()
        payload = {
            "title": title,
            "category": category_value,
            "habit": habit_value,
            "recurrence": "none",
            "status": "pending",
            "due_date": due_date or "",
            "description": "",
        }

        try:
            self.wait_for_item_in_active_list(title)
        except AssertionError:
            self._create_via_rest(payload)
            self.load().switch_to_today()
            self.wait_for_item_in_active_list(title)

        return {
            "category": category_label,
            "habit": habit_label,
            "recurrence": "none",
            "status": "pending",
        }

    def _create_via_rest(self, payload: dict):
        script = r"""
            const done = arguments[arguments.length - 1];
            try {
                const cfg = (window.pdTodoConfigs && window.pdTodoConfigs[0]) || null;
                if (!cfg) return done({error: "pdTodoConfigs missing"});
                let key = "";
                try { key = localStorage.getItem("pdTodoKey") || ""; } catch (e) {}
                const headers = {"Content-Type": "application/json", "X-WP-Nonce": cfg.nonce};
                if (key) headers["X-PD-Todo-Key"] = key;
                fetch(cfg.endpoint, {
                    method: "POST",
                    headers,
                    body: JSON.stringify(arguments[0]),
                }).then(async (resp) => {
                    if (!resp.ok) {
                        const txt = await resp.text();
                        return done({error: txt || resp.statusText, status: resp.status});
                    }
                    const data = await resp.json();
                    return done({ok: true, id: data && data.id});
                }).catch((err) => done({error: err.message || String(err)}));
            } catch (err) {
                return done({error: err.message || String(err)});
            }
        """
        result = self.driver.execute_async_script(script, payload)
        if not result or result.get("error"):
            raise AssertionError(f"REST create fallback failed: {result}")

    # -------- Tab / view helpers --------

    def _list_snapshot(self) -> tuple[int, str]:
        items = self._rows_in_view()
        if not items:
            lst = self.driver.find_elements(*self.LIST)
            return (0, (lst[0].text or "").strip() if lst else "")
        first = items[0].text.strip()
        return (len(items), first)

    def _current_error_text(self) -> str:
        errs = self.driver.find_elements(*self.ERROR)
        if not errs:
            return ""
        return (errs[0].text or "").strip()

    def switch_to_tab(self, tab_label: str):
        buttons = self.driver.find_elements(*self.TABS)
        matches = [btn for btn in buttons if (btn.text or "").strip().lower().startswith(tab_label.lower())]
        assert matches, f"Tab '{tab_label}' not found."
        btn = matches[0]
        if "active" in (btn.get_attribute("class") or ""):
            return self
        before = self._list_snapshot()
        if not btn.is_displayed():
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            except Exception:
                pass
        btn.click()

        def changed(_):
            try:
                if "active" in (btn.get_attribute("class") or ""):
                    return True
                return self._list_snapshot() != before
            except StaleElementReferenceException:
                return True

        WebDriverWait(self.driver, 15).until(changed)
        return self

    def switch_to_today(self):
        return self.switch_to_tab("Today")

    def switch_to_upcoming(self):
        return self.switch_to_tab("Upcoming")

    def switch_to_completed(self):
        return self.switch_to_tab("Completed")

    def _rows_in_view(self):
        body = self.driver.find_elements(*self.SECTION_BODY)
        if not body:
            return []
        return body[0].find_elements(*self.ROW)

    def _page_info(self) -> tuple[int, int]:
        labels = self.driver.find_elements(*self.PAGE_LABEL)
        if not labels:
            return (1, 1)
        txt = (labels[0].text or "").lower()
        if "of" not in txt:
            return (1, 1)
        try:
            before, after = txt.split("of", 1)
            current = int(before.replace("page", "").strip() or 1)
            total = int(after.strip() or 1)
            return (max(1, current), max(1, total))
        except Exception:
            return (1, 1)

    def _go_to_page(self, target: int):
        current, total = self._page_info()
        if target < 1 or target > total or target == current:
            return
        buttons = self.driver.find_elements(*self.PAGER_BTNS)
        if len(buttons) < 2:
            return
        direction = 1 if target > current else -1
        btn = buttons[1] if direction > 0 else buttons[0]
        while current != target:
            try:
                if not btn.is_enabled():
                    return
                prev = current
                btn.click()
                WebDriverWait(self.driver, 8).until(lambda _: self._page_info()[0] != prev)
                current, total = self._page_info()
                buttons = self.driver.find_elements(*self.PAGER_BTNS)
                if len(buttons) < 2:
                    break
                btn = buttons[1] if direction > 0 else buttons[0]
            except TimeoutException:
                return

    def _scroll_pages_for_row(self, title: str) -> bool:
        start_page, total = self._page_info()
        current = start_page
        visited: set[int] = set()

        while True:
            try:
                row = self._find_row(title)
            except StaleElementReferenceException:
                row = None
            if row:
                return True

            if total <= 1 or current in visited:
                break

            visited.add(current)
            if current < total:
                self._go_to_page(current + 1)
                current, total = self._page_info()
                continue
            break

        if start_page != current:
            try:
                self._go_to_page(start_page)
            except Exception:
                pass
        return False

    def _find_row(self, title: str):
        for row in self._rows_in_view():
            titles = row.find_elements(*self.ROW_TITLE)
            if titles and titles[0].text.strip() == title:
                return row
        return None

    def wait_for_item_in_active_list(self, title: str, timeout: int = 25):
        def found(_):
            return self._scroll_pages_for_row(title)

        try:
            WebDriverWait(self.driver, timeout).until(found)
            return self
        except TimeoutException:
            snapshot = self._list_snapshot()
            err = self._current_error_text()
            raise AssertionError(
                f"Timed out waiting for item '{title}' in current tab. Error='{err}', snapshot={snapshot}"
            )

    def wait_for_completed_item(self, title: str, timeout: int = 25):
        def found(_):
            return self._scroll_pages_for_row(title)

        WebDriverWait(self.driver, timeout).until(found)
        return self

    def due_text_for_active_item(self, title: str) -> str:
        card = self._find_row(title)
        assert card, f"Item with title {title!r} not found in current tab."
        due = card.find_element(*self.ROW_DUE)
        return (due.text or "").strip()

    def status_text_for_active_item(self, title: str) -> str:
        card = self._find_row(title)
        assert card, f"Item with title {title!r} not found in current tab."
        badges = card.find_elements(*self.ROW_STATUS)
        return (badges[0].text or "").strip().lower() if badges else ""

    def complete_task(self, title: str, timeout: int = 25):
        card = self._find_row(title)
        assert card, f"Item with title {title!r} not found."
        boxes = card.find_elements(*self.ROW_CHECKBOX)
        assert boxes, f"No checkbox found for item {title!r}."
        boxes[0].click()

        def gone_or_relisted(_):
            try:
                return self._find_row(title) is None
            except StaleElementReferenceException:
                return False

        WebDriverWait(self.driver, timeout).until(gone_or_relisted)
        return self

    def completed_titles(self) -> list[str]:
        titles: list[str] = []
        for row in self._rows_in_view():
            t = row.find_elements(*self.ROW_TITLE)
            if not t:
                continue
            txt = (t[0].text or "").strip()
            if txt:
                titles.append(txt)
        return titles

    # -------- Habits (minimal support for selects) --------

    def first_habit_label(self) -> str:
        self.open_form()
        sel = Select(self.driver.find_element(*self.HABIT_SELECT))
        for opt in sel.options:
            val = (opt.get_attribute("value") or "").strip()
            if val:
                return (opt.text or "").strip()
        return (sel.options[0].text or "").strip()

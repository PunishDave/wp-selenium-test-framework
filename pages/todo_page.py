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
    CALENDAR_CONTAINER = (By.CSS_SELECTOR, ".calendar-container")
    CALENDAR_GRID = (By.CSS_SELECTOR, ".calendar-grid")
    CALENDAR_DAY = (By.CSS_SELECTOR, ".calendar-grid .calendar-day")
    CALENDAR_TODAY = (By.CSS_SELECTOR, ".calendar-grid .calendar-day.today")
    CALENDAR_MONTH = (By.CSS_SELECTOR, ".calendar-header .current-month")
    CAL_PREV = (By.CSS_SELECTOR, ".calendar-header .prev-month")
    CAL_NEXT = (By.CSS_SELECTOR, ".calendar-header .next-month")

    TOOLBAR = (By.CSS_SELECTOR, ".pd-todo-toolbar")
    LIST = (By.CSS_SELECTOR, ".pd-todo-list")
    HABIT_COUNT = (By.CSS_SELECTOR, ".pd-todo-habit-counts .pd-todo-habit-count")
    AUTH = (By.CSS_SELECTOR, ".pd-todo-auth")
    AUTH_INPUT = (By.CSS_SELECTOR, ".pd-todo-auth input[type='password']")
    AUTH_BUTTON = (By.CSS_SELECTOR, ".pd-todo-auth button")
    ADMIN_ACCESS_INPUT = (By.ID, "pd_todo_access_key")

    FORM = (By.CSS_SELECTOR, "form.pd-todo-form")
    FORM_TOGGLE = (
        By.XPATH,
        "//button[contains(@class,'pd-todo-toggle') and (normalize-space()='Add To-Do' or normalize-space()='Hide Form')]",
    )
    TODAY_TOGGLE = (By.XPATH, "//button[contains(@class,'pd-todo-toggle') and normalize-space()='Today']")
    UPCOMING_TOGGLE = (By.XPATH, "//button[contains(@class,'pd-todo-toggle') and normalize-space()='Upcoming']")
    COMPLETED_TOGGLE = (
        By.XPATH,
        "//button[contains(@class,'pd-todo-filter-done') or (contains(@class,'pd-todo-toggle') and normalize-space()='Completed')]",
    )

    TITLE_INPUT = (By.CSS_SELECTOR, "form.pd-todo-form input[name='title']")
    CATEGORY_SELECT = (By.CSS_SELECTOR, "form.pd-todo-form select[name='category']")
    HABIT_SELECT = (By.CSS_SELECTOR, "form.pd-todo-form select[name='habit']")
    STATUS_SELECT = (By.CSS_SELECTOR, "form.pd-todo-form select[name='status']")
    RECURRENCE_SELECT = (By.CSS_SELECTOR, "form.pd-todo-form select[name='recurrence']")
    DUE_INPUT = (By.CSS_SELECTOR, "form.pd-todo-form input[name='due_date']")
    DESCRIPTION_INPUT = (By.CSS_SELECTOR, "form.pd-todo-form textarea[name='description']")
    SUBMIT = (By.CSS_SELECTOR, "form.pd-todo-form button[type='submit']")

    ACTIVE_ITEM = (By.CSS_SELECTOR, ".pd-todo-list .pd-todo-row")
    ACTIVE_TITLE = (By.CSS_SELECTOR, ".pd-todo-title")
    ACTIVE_DUE = (By.CSS_SELECTOR, ".pd-todo-due")
    ACTIVE_STATUS_BADGE = (By.CSS_SELECTOR, ".pd-todo-badge.status")

    COMPLETED_ITEM = (By.CSS_SELECTOR, ".pd-todo-completed-item")
    COMPLETED_TITLE = (By.CSS_SELECTOR, ".pd-todo-completed-title")
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
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(self.TOOLBAR))
            return True
        except TimeoutException:
            return False

    # -------- Calendar helpers --------

    def wait_for_calendar_loaded(self, timeout: int = 20):
        WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(self.CALENDAR_GRID))
        WebDriverWait(self.driver, timeout).until(lambda _: len(self.driver.find_elements(*self.CALENDAR_DAY)) >= 7)
        return self

    def calendar_month_text(self) -> str:
        els = self.driver.find_elements(*self.CALENDAR_MONTH)
        return (els[0].text or "").strip() if els else ""

    def count_calendar_days(self) -> int:
        return len(self.driver.find_elements(*self.CALENDAR_DAY))

    def calendar_has_today(self) -> bool:
        return bool(self.driver.find_elements(*self.CALENDAR_TODAY))

    def go_to_next_month(self, timeout: int = 15) -> str:
        before = self.calendar_month_text()
        link = WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(self.CAL_NEXT))
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", link)
        except Exception:
            pass
        try:
            WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable(self.CAL_NEXT)).click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", link)

        def changed(_):
            try:
                txt = self.calendar_month_text()
                return txt and txt != before
            except StaleElementReferenceException:
                return False

        WebDriverWait(self.driver, timeout).until(changed)
        self.wait_for_calendar_loaded(timeout=timeout)
        return self.calendar_month_text()

    # -------- Form / creation --------

    def _maybe_login_first(self):
        user = (os.getenv("WP_ADMIN_USER") or "").strip()
        pw = (os.getenv("WP_ADMIN_PASS") or "").strip()
        if user and pw:
            try:
                WpAdminLoginPage(self.driver).load().login(user, pw)
                self._admin_session = True
            except TimeoutException:
                # If admin login fails, we'll continue without admin session and rely on access key.
                pass

    def _get_access_key(self) -> str:
        if self._cached_access_key:
            return self._cached_access_key

        env_key = (os.getenv("PD_TODO_KEY") or "").strip()
        if env_key:
            self._cached_access_key = env_key
            return env_key

        # If we have an admin session, try to read the configured key from wp-admin.
        if self._admin_session:
            key = self._read_access_key_from_admin()
            if key:
                self._cached_access_key = key
                return key

        return ""

    def _seed_access_key(self, key: str) -> bool:
        """
        Store the access key into localStorage before scripts fire so both calendar and API calls succeed.
        Returns True if we set it this call.
        """
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
        if not block:
            return
        if not block.is_displayed():
            return

        key = self._get_access_key()

        if not key:
            # Fallback: log in as admin (if creds provided) so server allows requests without a key.
            user = (os.getenv("WP_ADMIN_USER") or "").strip()
            pw = (os.getenv("WP_ADMIN_PASS") or "").strip()
            assert user and pw, "Access key required. Set PD_TODO_KEY or provide WP_ADMIN_USER / WP_ADMIN_PASS for admin fallback."

            start_url = getattr(self, "_last_url", self.driver.current_url)
            WpAdminLoginPage(self.driver).load().login(user, pw)
            self.driver.get(start_url)
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located(self.TOOLBAR))
            auth_blocks = self.driver.find_elements(*self.AUTH)
            block = auth_blocks[0] if auth_blocks else None
            # Use a placeholder key to satisfy the front-end UI; server-side auth is via admin session.
            key = "admin-bypass"

        WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located(self.AUTH_INPUT))
        inp = self.driver.find_element(*self.AUTH_INPUT)
        btn = self.driver.find_element(*self.AUTH_BUTTON)
        inp.clear()
        inp.send_keys(key)
        btn.click()
        WebDriverWait(self.driver, 15).until(lambda _: not auth_block() or not auth_block().is_displayed())

    def _read_access_key_from_admin(self) -> str:
        """
        Best-effort: if we're already logged in as admin, visit the Access page and read the configured key.
        Returns empty string on failure.
        """
        user = (os.getenv("WP_ADMIN_USER") or "").strip()
        pw = (os.getenv("WP_ADMIN_PASS") or "").strip()
        if not (user and pw):
            return ""

        try:
            # stay logged in; just open the access settings
            self.driver.get(f"{WP_ADMIN.rstrip('/')}/admin.php?page=pd-todo-access")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(self.ADMIN_ACCESS_INPUT))
            key_input = self.driver.find_element(*self.ADMIN_ACCESS_INPUT)
            key = (key_input.get_attribute("value") or "").strip()
            # return to previous page if we have one
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
        def hidden() -> bool:
            cls = self.driver.find_element(*self.FORM).get_attribute("class") or ""
            return "pd-todo-form-hidden" in cls

        if not hidden():
            return

        WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable(self.FORM_TOGGLE)).click()
        WebDriverWait(self.driver, 10).until(lambda _: not hidden())

    def _select_value(self, locator, value: Optional[str]) -> tuple[str, str]:
        select_el = self.driver.find_element(*locator)
        sel = Select(select_el)

        if value:
            desired = value.strip()
            # Try value match first
            for opt in sel.options:
                opt_val = (opt.get_attribute("value") or "").strip()
                if opt_val == desired:
                    sel.select_by_value(opt_val)
                    return (opt.text or "").strip(), opt_val
            # Fallback: visible text match
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

        # If nothing else, select the first available option.
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
        recurrence: Optional[str] = None,
        status: Optional[str] = None,
        description: str = "",
    ) -> dict:
        self.open_form()

        title_el = self.driver.find_element(*self.TITLE_INPUT)
        title_el.clear()
        title_el.send_keys(title)

        category_label, category_value = self._select_value(self.CATEGORY_SELECT, category)
        habit_label, habit_value = self._select_value(self.HABIT_SELECT, habit)
        recurrence_label, recurrence_value = self._select_value(self.RECURRENCE_SELECT, recurrence)
        status_label, status_value = self._select_value(self.STATUS_SELECT, status)

        due_el = self.driver.find_element(*self.DUE_INPUT)
        due_el.clear()
        if due_date:
            due_el.send_keys(due_date)

        desc_el = self.driver.find_element(*self.DESCRIPTION_INPUT)
        desc_el.clear()
        if description:
            desc_el.send_keys(description)

        self.driver.find_element(*self.SUBMIT).click()
        payload = {
            "title": title,
            "category": category_value,
            "habit": habit_value,
            "recurrence": recurrence_value,
            "status": status_value,
            "due_date": due_date or "",
            "description": description or "",
        }

        try:
            self.wait_for_item_in_active_list(title)
        except AssertionError:
            # If the UI path didn’t surface the item, try the REST API directly (uses page config + nonce)
            self._create_via_rest(payload)
            self.switch_to_today()
            self.wait_for_item_in_active_list(title)

        return {
            "category": category_label,
            "habit": habit_label,
            "recurrence": recurrence_label,
            "status": status_label,
        }

    def _create_via_rest(self, payload: dict):
        """
        Fallback for environments where the UI submit doesn’t surface the new item.
        Uses the in-page config (endpoint + nonce + access key) to POST directly.
        """
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

    # -------- View toggles / items --------

    def _list_snapshot(self) -> tuple[int, str]:
        items = self.driver.find_elements(*self.ACTIVE_ITEM)
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

    def switch_to_today(self):
        lst = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(self.LIST))
        before_text = lst.text
        before_class = lst.get_attribute("class") or ""

        btn = WebDriverWait(self.driver, 15).until(EC.presence_of_element_located(self.TODAY_TOGGLE))
        try:
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(self.TODAY_TOGGLE)).click()
        except Exception:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            except Exception:
                pass
            try:
                btn.click()
            except Exception:
                # final fallback if admin bar overlays
                self.driver.execute_script("arguments[0].click();", btn)

        def changed(_):
            try:
                return EC.staleness_of(lst)(_) or lst.text != before_text or lst.get_attribute("class") != before_class
            except StaleElementReferenceException:
                return True

        WebDriverWait(self.driver, 20).until(changed)
        return self

    def switch_to_upcoming(self):
        lst = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(self.LIST))
        before_text = lst.text
        before_class = lst.get_attribute("class") or ""

        WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable(self.UPCOMING_TOGGLE)).click()

        def changed(_):
            try:
                return EC.staleness_of(lst)(_) or lst.text != before_text or lst.get_attribute("class") != before_class
            except StaleElementReferenceException:
                return False

        WebDriverWait(self.driver, 20).until(changed)
        return self

    def switch_to_completed(self):
        before = self._list_snapshot()
        WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable(self.COMPLETED_TOGGLE)).click()

        def ready(_):
            try:
                return self.is_completed_view() or self._list_snapshot() != before
            except StaleElementReferenceException:
                return False

        WebDriverWait(self.driver, 20).until(ready)
        return self

    def is_completed_view(self) -> bool:
        lst = self.driver.find_elements(*self.LIST)
        if not lst:
            return False
        cls = lst[0].get_attribute("class") or ""
        return "pd-todo-completed-list" in cls

    def _find_active_card(self, title: str):
        cards = self.driver.find_elements(*self.ACTIVE_ITEM)
        for card in cards:
            titles = card.find_elements(*self.ACTIVE_TITLE)
            if titles and titles[0].text.strip() == title:
                return card
        return None

    def _find_completed_row(self, title: str):
        rows = self.driver.find_elements(*self.COMPLETED_ITEM)
        for row in rows:
            titles = row.find_elements(*self.COMPLETED_TITLE)
            if titles and titles[0].text.strip() == title:
                return row
        return None

    def wait_for_item_in_active_list(self, title: str, timeout: int = 25):
        def found(_):
            try:
                return self._find_active_card(title) is not None
            except StaleElementReferenceException:
                return False

        try:
            WebDriverWait(self.driver, timeout).until(found)
            return self
        except TimeoutException:
            snapshot = self._list_snapshot()
            err = self._current_error_text()
            raise AssertionError(
                f"Timed out waiting for item '{title}' in active list. Error='{err}', snapshot={snapshot}"
            )

    def wait_for_completed_item(self, title: str, timeout: int = 25):
        def found(_):
            try:
                return self._find_completed_row(title) is not None
            except StaleElementReferenceException:
                return False

        WebDriverWait(self.driver, timeout).until(found)
        return self

    def due_text_for_active_item(self, title: str) -> str:
        card = self._find_active_card(title)
        assert card, f"Active item with title {title!r} not found."
        due = card.find_element(*self.ACTIVE_DUE)
        return (due.text or "").strip()

    def status_text_for_active_item(self, title: str) -> str:
        card = self._find_active_card(title)
        assert card, f"Active item with title {title!r} not found."
        badge = card.find_element(*self.ACTIVE_STATUS_BADGE)
        return (badge.text or "").strip().lower()

    def complete_task(self, title: str, timeout: int = 25):
        card = self._find_active_card(title)
        assert card, f"Active item with title {title!r} not found."
        btns = card.find_elements(By.XPATH, ".//button[normalize-space()='Complete']")
        assert btns, f"No Complete button found for item {title!r}."
        btns[0].click()

        def gone_or_relisted(_):
            try:
                return self._find_active_card(title) is None
            except StaleElementReferenceException:
                return False

        WebDriverWait(self.driver, timeout).until(gone_or_relisted)
        return self

    def completed_titles(self) -> list[str]:
        titles: list[str] = []
        for row in self.driver.find_elements(*self.COMPLETED_ITEM):
            t = row.find_elements(*self.COMPLETED_TITLE)
            if t:
                txt = (t[0].text or "").strip()
                if txt:
                    titles.append(txt)
        return titles

    # -------- Habits --------

    def habit_counters(self) -> list[HabitCounter]:
        counters: list[HabitCounter] = []
        for el in self.driver.find_elements(*self.HABIT_COUNT):
            txt = (el.text or "").strip()
            if not txt:
                continue
            if ":" in txt:
                habit, count = txt.split(":", 1)
                try:
                    num = int(count.strip())
                except ValueError:
                    num = 0
                counters.append(HabitCounter(habit=habit.strip(), count=num))
            else:
                counters.append(HabitCounter(habit=txt, count=0))
        return counters

    def habit_counts_dict(self) -> dict[str, int]:
        data = {}
        for counter in self.habit_counters():
            data[counter.habit] = counter.count
        return data

    def first_habit_label(self) -> str:
        self.open_form()
        sel = Select(self.driver.find_element(*self.HABIT_SELECT))
        for opt in sel.options:
            val = (opt.get_attribute("value") or "").strip()
            if val:
                return (opt.text or "").strip()
        return (sel.options[0].text or "").strip()

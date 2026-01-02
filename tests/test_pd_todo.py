from __future__ import annotations

import os
import time
from datetime import date

import pytest

from pages.todo_page import TodoPage
from pages.wp_admin_login_page import WpAdminLoginPage
from pages.wp_admin_todo_page import WpAdminTodoPage
from pages.wp_admin_todo_settings_page import WpAdminTodoSettingsPage


def _today_str() -> str:
    return date.today().isoformat()


def _unique_title(prefix: str) -> str:
    return f"{prefix} {int(time.time() * 1000)}"


_todo_prepared = False


@pytest.fixture(autouse=True)
def _ensure_todo_baseline(driver):
    """
    Align the test expectations with the plugin:
    - Ensure at least one category and habit exist (so creation isn't rejected).
    - If an access key exists and PD_TODO_KEY isn't provided, capture it for front-end use.
    Runs once per test session (guarded by _todo_prepared).
    """
    global _todo_prepared
    if _todo_prepared:
        return

    user = (os.getenv("WP_ADMIN_USER") or "").strip()
    pw = (os.getenv("WP_ADMIN_PASS") or "").strip()
    explicit_key = (os.getenv("PD_TODO_KEY") or "").strip()

    if user and pw:
        WpAdminLoginPage(driver).load().login(user, pw)
        settings = WpAdminTodoSettingsPage(driver)

        cats = settings.read_categories()
        if not cats:
            settings.set_categories(["General"])

        habits = settings.read_habits()
        if not habits:
            settings.set_habits(["Default"])

        key = settings.read_access_key()
        if key and not explicit_key:
            os.environ["PD_TODO_KEY"] = key

        _todo_prepared = True
        return

    # No admin; fall back to explicit key only
    if explicit_key:
        _todo_prepared = True
        return

    pytest.skip("Set PD_TODO_KEY or WP_ADMIN_USER/WP_ADMIN_PASS to prepare To-Do baseline.")


@pytest.fixture(autouse=True, scope="module")
def _require_todo_auth():
    """
    Avoid long timeouts when the To-Do plugin is locked.
    Require either PD_TODO_KEY or WP_ADMIN credentials to be provided.
    """
    has_key = (os.getenv("PD_TODO_KEY") or "").strip()
    has_admin = (os.getenv("WP_ADMIN_USER") or "").strip() and (os.getenv("WP_ADMIN_PASS") or "").strip()
    if not (has_key or has_admin):
        pytest.skip("Set PD_TODO_KEY or WP_ADMIN_USER/WP_ADMIN_PASS to run To-Do tests.")


def _get_admin_creds() -> tuple[str, str]:
    user = (os.getenv("WP_ADMIN_USER") or "").strip()
    pw = (os.getenv("WP_ADMIN_PASS") or "").strip()
    assert user and pw, "WP_ADMIN_USER / WP_ADMIN_PASS not set."
    return user, pw


def test_todo_add_and_complete_task(driver):
    page = TodoPage(driver).load()
    title = _unique_title("Selenium To-Do")

    page.add_task(title, _today_str())
    page.wait_for_item_in_active_list(title)
    page.complete_task(title)

    page.switch_to_completed().wait_for_completed_item(title)
    assert title in page.completed_titles()


def test_wp_admin_todo_bulk_actions(driver):
    page = TodoPage(driver).load()
    base = _unique_title("Selenium Bulk")
    titles = [f"{base} A", f"{base} B"]

    for t in titles:
        page.add_task(t, _today_str())
        page.wait_for_item_in_active_list(t)

    user, pw = _get_admin_creds()
    WpAdminLoginPage(driver).load().login(user, pw)

    admin_page = WpAdminTodoPage(driver).open()
    admin_page.search(base)
    admin_page.select_rows_by_title(titles)
    admin_page.apply_bulk_action("mark_done")

    statuses = [admin_page.status_for_title(t).lower() for t in titles]
    assert all("done" in s for s in statuses), f"Statuses after bulk update: {statuses}"

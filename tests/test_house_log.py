from __future__ import annotations

import os
import time

import pytest

from pages.house_log_page import HouseLogPage
from pages.wp_admin_login_page import WpAdminLoginPage
from pages.wp_admin_house_log_page import WpAdminHouseLogPage
from pages.wp_admin_house_log_issue_form_page import WpAdminHouseLogIssueFormPage


def _unique_title(prefix: str) -> str:
    return f"{prefix} {int(time.time() * 1000)}"


def _get_admin_creds() -> tuple[str, str]:
    user = (os.getenv("WP_ADMIN_USER") or "").strip()
    pw = (os.getenv("WP_ADMIN_PASS") or "").strip()
    if not (user and pw):
        pytest.skip("WP_ADMIN_USER / WP_ADMIN_PASS not set.")
    return user, pw


def _skip_if_locked(page: HouseLogPage):
    if page.is_locked() and not page.has_access_key():
        pytest.skip("House Log is locked. Set PD_HOUSE_LOG_KEY to run this test.")


def test_house_log_frontend_add_and_remove(driver):
    page = HouseLogPage(driver).load()
    _skip_if_locked(page)

    title = _unique_title("Selenium House Issue")
    page.add_issue(title, "Leak under the sink")
    assert title in page.issue_titles()

    page.delete_issue(title)
    assert title not in page.issue_titles()


def test_house_log_frontend_reorder(driver):
    page = HouseLogPage(driver).load()
    _skip_if_locked(page)

    title_a = _unique_title("Selenium House A")
    title_b = _unique_title("Selenium House B")

    page.add_issue(title_a, "Test A")
    page.add_issue(title_b, "Test B")

    page.reorder_issue_before(title_b, title_a)
    titles = page.issue_titles()
    assert titles.index(title_b) < titles.index(title_a)

    page.delete_issue(title_a)
    page.delete_issue(title_b)


def test_house_log_admin_crud(driver):
    user, pw = _get_admin_creds()
    WpAdminLoginPage(driver).load().login(user, pw)

    form = WpAdminHouseLogIssueFormPage(driver).open()
    title = _unique_title("Admin House Issue")
    list_page = form.save(title=title, details="Front door hinge", priority=1)
    assert list_page.has_title(title)

    issue_id = list_page.get_issue_id(title)
    assert issue_id > 0

    updated_title = _unique_title("Admin House Issue Updated")
    form = WpAdminHouseLogIssueFormPage(driver).open_edit(issue_id)
    list_page = form.save(title=updated_title, details="Front door hinge - updated", priority=1)
    assert list_page.has_title(updated_title)

    list_page.delete_issue(updated_title)
    assert not list_page.has_title(updated_title)

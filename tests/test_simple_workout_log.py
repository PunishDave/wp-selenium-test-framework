import os
import time
from datetime import date

import pytest

from pages.workout_log_page import WorkoutLogPage
from pages.wp_admin_login_page import WpAdminLoginPage
from pages.wp_admin_swl_entries_page import WpAdminSwlEntriesPage
from pages.wp_admin_swl_schedule_page import WpAdminSwlSchedulePage


def _today() -> str:
    return date.today().isoformat()


def _unique(label: str) -> str:
    return f"{label} {int(time.time())}"


def _get_admin_creds() -> tuple[str, str]:
    user = (os.getenv("WP_ADMIN_USER") or "").strip()
    pw = (os.getenv("WP_ADMIN_PASS") or "").strip()
    if not (user and pw):
        pytest.skip("WP_ADMIN_USER / WP_ADMIN_PASS not set.")
    return user, pw


def test_workout_log_frontend_lists_days_and_cards(driver):
    page = WorkoutLogPage(driver).load()
    days = page.day_buttons_texts()
    assert days, "Expected at least one workout day button."

    page.select_day_by_index(0)
    page.wait_for_cards()

    titles = page.card_titles()
    assert titles, "Expected at least one workout card for the first day."
    assert all(t for t in titles), "Card titles should not be empty."


def test_workout_log_frontend_allows_update(driver):
    page = WorkoutLogPage(driver).load().select_day_by_index(0)
    before = page.first_card_snapshot()
    assert before, "No workout cards found to update."

    weight = f"{int(time.time()) % 200}kg"
    reps = 3
    page.update_first_card(weight=weight, reps=reps)
    after = page.first_card_snapshot()

    assert after["weight"].lower() == weight.lower(), "Weight did not persist after update."
    if after["reps"]:
        assert after["reps"] == str(reps), "Reps did not persist after update."
    if after["meta"]:
        assert _today() in after["meta"], "Last done meta should reflect today after update."


def test_wp_admin_swl_schedule_save(driver):
    user, pw = _get_admin_creds()
    WpAdminLoginPage(driver).load().login(user, pw)

    schedule = WpAdminSwlSchedulePage(driver).open()
    assert schedule.row_count() > 0, "Expected schedule rows to exist."

    new_label = _unique("Selenium Day")
    schedule.update_first_label(new_label)


def test_wp_admin_swl_entries_quick_add(driver):
    user, pw = _get_admin_creds()
    WpAdminLoginPage(driver).load().login(user, pw)

    entries = WpAdminSwlEntriesPage(driver).open()
    workout = _unique("Selenium Entry")
    entries.add_entry(workout=workout, weight="50kg", reps=5, notes="Added by Selenium", performed_on=_today())

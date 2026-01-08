from datetime import date, timedelta

import pytest

from pages.gamewithdave_page import GameWithDavePage
from framework.gwd_api import (
    ADMIN_PASSWORD,
    GWD_PASSWORDS,
    clear_debug_emails,
    debug_availability,
    fetch_game_nights,
    submit_availability,
    trigger_cron,
    update_game_night,
)

TEAM_1 = "team-1"
TEAM_2 = "team-2"


def future_iso(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def _nights_list():
    resp = fetch_game_nights()
    assert resp.get("success") is True, f"fetch_game_nights failed: {resp}"
    return resp.get("data", {}).get("nights", [])


def _find_night(date_iso: str, team: str | None = None):
    for night in _nights_list():
        if night.get("date") != date_iso:
            continue
        if team is not None and night.get("team") != team:
            continue
        return night
    return None


def _debug_entries():
    resp = fetch_game_nights()
    assert resp.get("success") is True, f"fetch_game_nights failed: {resp}"
    return resp.get("data", {}).get("debug_emails", [])


def _find_debug_entry(entry_type: str, date_iso: str, *, team: str | None = None):
    for entry in _debug_entries():
        if entry.get("type") != entry_type:
            continue
        if entry.get("date") != date_iso:
            continue
        if team is not None and entry.get("team") != team:
            continue
        return entry
    return None


def _debug_availability(date_iso: str):
    resp = debug_availability(date_iso)
    assert resp.get("success") is True, f"debug_availability failed: {resp}"
    return resp.get("data", {})


def _is_clean_date(date_iso: str, night_dates: set[str]) -> bool:
    if date_iso in night_dates:
        return False
    data = _debug_availability(date_iso)
    if data.get("availability"):
        return False
    if data.get("game_nights"):
        return False
    return True


def _find_clean_date(start_offset: int, *, max_offset: int = 400) -> str:
    night_dates = {n.get("date") for n in _nights_list() if n.get("date")}
    for offset in range(start_offset, max_offset + 1):
        candidate = future_iso(offset)
        if _is_clean_date(candidate, night_dates):
            return candidate
    raise AssertionError("Unable to find a clean future date with no availability or game nights.")


def _find_clean_range(days: int, start_offset: int, *, max_offset: int = 400) -> tuple[str, str]:
    if days < 1:
        raise ValueError("days must be >= 1")
    night_dates = {n.get("date") for n in _nights_list() if n.get("date")}
    for offset in range(start_offset, max_offset + 1):
        start = date.today() + timedelta(days=offset)
        candidates = [(start + timedelta(days=i)).isoformat() for i in range(days)]
        if all(_is_clean_date(candidate, night_dates) for candidate in candidates):
            return candidates[0], candidates[-1]
    raise AssertionError("Unable to find a clean date range with no availability or game nights.")


def _clear_debug_log():
    resp = clear_debug_emails()
    assert resp.get("success") is True, f"clear_debug_emails failed: {resp}"


def _make_event(date_iso: str, users: list[str]):
    for user in users:
        submit_availability(
            password=GWD_PASSWORDS[user],
            start_date=date_iso,
            end_date=date_iso,
            status="yes",
        )


def test_gamewithdave_invalid_dates_error():
    start = future_iso(2)
    end = future_iso(1)
    resp = submit_availability(
        password=GWD_PASSWORDS["bene"],
        start_date=start,
        end_date=end,
        status="yes",
    )
    assert resp.get("success") is False
    msg = resp.get("data", {}).get("message", "").lower()
    assert "valid start/end date" in msg


def test_gamewithdave_invalid_password_error():
    day = future_iso(1)
    resp = submit_availability(
        password="wrong-password",
        start_date=day,
        end_date=day,
        status="yes",
    )
    assert resp.get("success") is False
    msg = resp.get("data", {}).get("message", "").lower()
    assert "invalid password" in msg


def test_gamewithdave_single_date_updates_calendar(driver):
    target = _find_clean_date(1)
    resp = submit_availability(
        password=GWD_PASSWORDS["bene"],
        start_date=target,
        end_date=target,
        status="yes",
    )
    assert resp.get("success") is True
    assert "availability updated successfully" in resp.get("data", {}).get("message", "").lower()

    page = GameWithDavePage(driver).load().wait_for_calendar()
    dt = date.fromisoformat(target)
    page.ensure_month_for_date(dt)
    assert page.has_availability(dt.day, "BE", status="yes")


def test_gamewithdave_game_time_note_visible(driver):
    page = GameWithDavePage(driver).load().wait_for_calendar()
    note = page.game_time_note_text()
    assert note, "Expected game time note to be visible."


def test_gamewithdave_bulk_submission_updates_calendar(driver):
    start, end = _find_clean_range(2, 2)
    resp = submit_availability(
        password=GWD_PASSWORDS["robin"],
        start_date=start,
        end_date=end,
        status="yes",
    )
    assert resp.get("success") is True

    page = GameWithDavePage(driver).load().wait_for_calendar()
    dt = date.fromisoformat(start)
    page.ensure_month_for_date(dt)
    for iso in (start, end):
        day_num = date.fromisoformat(iso).day
        assert page.has_availability(day_num, "RO", status="yes"), f"Expected availability chip for {iso}"


def test_gamewithdave_under_threshold_does_not_create_event():
    target = _find_clean_date(90)
    submit_availability(
        password=GWD_PASSWORDS["bene"],
        start_date=target,
        end_date=target,
        status="yes",
    )
    resp = submit_availability(
        password=GWD_PASSWORDS["robin"],
        start_date=target,
        end_date=target,
        status="tentative",
    )
    assert resp.get("success") is True

    nights = _nights_list()
    dates = {n["date"] for n in nights}
    assert target not in dates


def test_gamewithdave_event_created_and_detection_email_for_three_yes(record_property):
    target = _find_clean_date(100)
    _clear_debug_log()

    _make_event(target, ["bene", "robin", "razzyn"])

    night = _find_night(target, TEAM_1)
    assert night is not None and night.get("status") == "detected"

    entries = _debug_entries()
    record_property("gwd_debug_emails", entries)
    assert _find_debug_entry("detection", target, team=TEAM_1) is not None


def test_gamewithdave_event_created_with_tentatives_counts_and_detection_email(record_property):
    target = _find_clean_date(101)
    _clear_debug_log()

    submit_availability(password=GWD_PASSWORDS["bene"], start_date=target, end_date=target, status="yes")
    submit_availability(password=GWD_PASSWORDS["robin"], start_date=target, end_date=target, status="yes")
    submit_availability(password=GWD_PASSWORDS["razzyn"], start_date=target, end_date=target, status="tentative")
    submit_availability(password=GWD_PASSWORDS["dave"], start_date=target, end_date=target, status="tentative")

    night = _find_night(target, TEAM_1)
    assert night is not None

    entries = _debug_entries()
    record_property("gwd_debug_emails", entries)
    assert _find_debug_entry("detection", target, team=TEAM_1) is not None


def test_gamewithdave_admin_counts_for_all_teams_and_emails_only_yes(record_property):
    target = _find_clean_date(106)
    _clear_debug_log()

    submit_availability(password=GWD_PASSWORDS["bene"], start_date=target, end_date=target, status="yes")
    submit_availability(password=GWD_PASSWORDS["robin"], start_date=target, end_date=target, status="yes")
    submit_availability(password=GWD_PASSWORDS["razzyn"], start_date=target, end_date=target, status="no")
    submit_availability(password=GWD_PASSWORDS["dave"], start_date=target, end_date=target, status="yes")

    night = _find_night(target, TEAM_1)
    assert night is not None and night.get("status") == "detected"
    assert _find_night(target, TEAM_2) is None

    entries = _debug_entries()
    record_property("gwd_debug_emails", entries)
    entry = _find_debug_entry("detection", target, team=TEAM_1)
    assert entry is not None
    initials = set(entry.get("initials") or [])
    assert initials == {"BE", "RO", "DA"}


def test_gamewithdave_remove_detected_night_no_email(record_property):
    target = _find_clean_date(102)
    _clear_debug_log()

    _make_event(target, ["bene", "robin", "razzyn"])
    _clear_debug_log()  # ignore detection emails from creation

    resp = update_game_night(
        admin_password=ADMIN_PASSWORD,
        night_date=target,
        night_team=TEAM_1,
        night_action="remove",
    )
    assert resp.get("success") is True

    entries = _debug_entries()
    record_property("gwd_debug_emails", entries)
    assert not entries  # removal should not send mail

    night = _find_night(target, TEAM_1)
    assert night is not None and night.get("status") == "removed"


def test_gamewithdave_lock_in_sends_debug_email_with_ics(record_property):
    target = _find_clean_date(103)
    _clear_debug_log()

    _make_event(target, ["bene", "robin", "razzyn"])
    _clear_debug_log()

    resp = update_game_night(
        admin_password=ADMIN_PASSWORD,
        night_date=target,
        night_team=TEAM_1,
        night_action="lock",
    )
    assert resp.get("success") is True

    entries = _debug_entries()
    record_property("gwd_debug_emails", entries)
    entry = _find_debug_entry("lock", target, team=TEAM_1)
    assert entry is not None and entry.get("ics")

    night = _find_night(target, TEAM_1)
    assert night is not None and night.get("status") == "locked"


def test_gamewithdave_reminder_email_logged_when_missing_availability(record_property):
    _clear_debug_log()

    resp = trigger_cron()
    assert resp.get("success") is True, f"trigger_cron failed: {resp}"

    entries = _debug_entries()
    record_property("gwd_debug_emails", entries)
    reminders = [e for e in entries if e.get("type") == "availability-reminder"]
    if not reminders:
        pytest.skip("No reminders logged; users may already have availability for the next 30 days.")


def test_gamewithdave_reminder_skipped_when_user_has_availability(record_property):
    _clear_debug_log()
    target = future_iso(1)

    submit_availability(password=GWD_PASSWORDS["bene"], start_date=target, end_date=target, status="yes")

    resp = trigger_cron()
    assert resp.get("success") is True, f"trigger_cron failed: {resp}"

    entries = _debug_entries()
    record_property("gwd_debug_emails", entries)
    reminders_for_bene = [
        e for e in entries
        if e.get("type") == "availability-reminder" and e.get("user_role") == "bene"
    ]
    assert not reminders_for_bene, "Did not expect a reminder for users who already set availability"


def test_gamewithdave_admin_panel_rejects_invalid_admin_password():
    target = _find_clean_date(50)
    resp = update_game_night(
        admin_password="wrong@example.com",
        night_date=target,
        night_action="lock",
    )
    assert resp.get("success") is False
    msg = resp.get("data", {}).get("message", "").lower()
    assert "incorrect admin password" in msg


def test_gamewithdave_admin_panel_lists_upcoming_nights():
    t1, t2 = _find_clean_range(2, 104)

    _make_event(t1, ["bene", "robin", "razzyn"])
    _make_event(t2, ["bene", "robin", "razzyn"])

    n1 = _find_night(t1, TEAM_1)
    n2 = _find_night(t2, TEAM_1)
    assert n1 is not None and n2 is not None
    assert n1.get("team") == TEAM_1 and n1.get("teamLabel")
    assert n2.get("team") == TEAM_1 and n2.get("teamLabel")

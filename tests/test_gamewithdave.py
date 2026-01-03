from datetime import date, timedelta

from pages.gamewithdave_page import GameWithDavePage
from framework.gwd_api import (
    ADMIN_PASSWORD,
    GWD_PASSWORDS,
    clear_debug_emails,
    fetch_game_nights,
    submit_availability,
    trigger_cron,
    update_game_night,
)


def future_iso(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def _nights_list():
    resp = fetch_game_nights()
    assert resp.get("success") is True, f"fetch_game_nights failed: {resp}"
    return resp.get("data", {}).get("nights", [])


def _debug_entries():
    resp = fetch_game_nights()
    assert resp.get("success") is True, f"fetch_game_nights failed: {resp}"
    return resp.get("data", {}).get("debug_emails", [])


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
    target = future_iso(1)
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


def test_gamewithdave_bulk_submission_updates_calendar(driver):
    start = future_iso(2)
    end = future_iso(3)
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
    target = future_iso(90)
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
    target = future_iso(100)
    _clear_debug_log()

    _make_event(target, ["bene", "robin", "razzyn"])

    nights = _nights_list()
    assert any(n["date"] == target and n.get("status") == "detected" for n in nights)

    entries = _debug_entries()
    record_property("gwd_debug_emails", entries)
    assert any(e.get("type") == "detection" and e.get("date") == target for e in entries)


def test_gamewithdave_event_created_with_tentatives_counts_and_detection_email(record_property):
    target = future_iso(101)
    _clear_debug_log()

    submit_availability(password=GWD_PASSWORDS["bene"], start_date=target, end_date=target, status="yes")
    submit_availability(password=GWD_PASSWORDS["robin"], start_date=target, end_date=target, status="yes")
    submit_availability(password=GWD_PASSWORDS["razzyn"], start_date=target, end_date=target, status="tentative")
    submit_availability(password=GWD_PASSWORDS["dave"], start_date=target, end_date=target, status="tentative")

    nights = _nights_list()
    assert any(n["date"] == target for n in nights)

    entries = _debug_entries()
    record_property("gwd_debug_emails", entries)
    assert any(e.get("type") == "detection" and e.get("date") == target for e in entries)


def test_gamewithdave_remove_detected_night_no_email(record_property):
    target = future_iso(102)
    _clear_debug_log()

    _make_event(target, ["bene", "robin", "razzyn"])
    _clear_debug_log()  # ignore detection emails from creation

    resp = update_game_night(
        admin_password=ADMIN_PASSWORD,
        night_date=target,
        night_action="remove",
    )
    assert resp.get("success") is True

    entries = _debug_entries()
    record_property("gwd_debug_emails", entries)
    assert not entries  # removal should not send mail

    nights = _nights_list()
    assert any(n["date"] == target and n.get("status") == "removed" for n in nights)


def test_gamewithdave_lock_in_sends_debug_email_with_ics(record_property):
    target = future_iso(103)
    _clear_debug_log()

    _make_event(target, ["bene", "robin", "razzyn"])
    _clear_debug_log()

    resp = update_game_night(
        admin_password=ADMIN_PASSWORD,
        night_date=target,
        night_action="lock",
    )
    assert resp.get("success") is True

    entries = _debug_entries()
    record_property("gwd_debug_emails", entries)
    assert any(
        e.get("type") == "lock"
        and e.get("date") == target
        and e.get("ics")
        for e in entries
    )

    nights = _nights_list()
    assert any(n["date"] == target and n.get("status") == "locked" for n in nights)


def test_gamewithdave_reminder_email_logged_when_missing_availability(record_property):
    _clear_debug_log()

    resp = trigger_cron()
    assert resp.get("success") is True, f"trigger_cron failed: {resp}"

    entries = _debug_entries()
    record_property("gwd_debug_emails", entries)
    reminders = [e for e in entries if e.get("type") == "availability-reminder"]
    assert reminders, "Expected at least one availability reminder email entry"


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
    target = future_iso(50)
    resp = update_game_night(
        admin_password="wrong@example.com",
        night_date=target,
        night_action="lock",
    )
    assert resp.get("success") is False
    msg = resp.get("data", {}).get("message", "").lower()
    assert "incorrect admin password" in msg


def test_gamewithdave_admin_panel_lists_upcoming_nights():
    t1 = future_iso(104)
    t2 = future_iso(105)

    _make_event(t1, ["bene", "robin", "razzyn"])
    _make_event(t2, ["bene", "robin", "razzyn"])

    nights = _nights_list()
    dates = {n["date"] for n in nights}
    assert {t1, t2}.issubset(dates)

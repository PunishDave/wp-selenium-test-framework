from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from framework import urls

GWD_PASSWORDS = {
    "bene": "Bene%Gaming2025",
    "robin": "Robin&Gaming2025",
    "razzyn": "Razzyn#Gaming2025",
    "dave": "Dave@Gaming2025",
}

ADMIN_PASSWORD = GWD_PASSWORDS["dave"]
CRON_SECRET = "k7Hh2f9sYxP4QzLm"


def _post(
    data: dict[str, str],
    *,
    timeout: float = 20.0,
    expect_json: bool = True,
) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        urls.ADMIN_AJAX,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode()
    if not expect_json:
        return {"success": True, "raw": body}
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Non-JSON response from admin-ajax: {body[:200]}") from e


def submit_availability(
    *,
    password: str,
    start_date: str,
    end_date: str,
    status: str,
    debug: bool = True,
) -> dict[str, Any]:
    payload: dict[str, str] = {
        "action": "submit_availability",
        "password": password,
        "start_date": start_date,
        "end_date": end_date,
        "availability_status": status,
    }
    if debug:
        payload["gwd_debug"] = "1"
    return _post(payload)


def load_calendar(*, year: int | None = None, month: int | None = None) -> dict[str, Any]:
    payload: dict[str, str] = {"action": "load_calendar"}
    if year is not None:
        payload["year"] = str(year)
    if month is not None:
        payload["month"] = str(month)
    return _post(payload)


def fetch_game_nights(
    admin_password: str = ADMIN_PASSWORD,
    *,
    debug: bool = True,
    debug_clear: bool = False,
) -> dict[str, Any]:
    payload: dict[str, str] = {
        "action": "gwd_fetch_game_nights",
        "admin_password": admin_password,
    }
    if debug:
        payload["gwd_debug"] = "1"
    if debug_clear:
        payload["gwd_debug_clear"] = "1"
    return _post(payload)


def update_game_night(
    *,
    admin_password: str = ADMIN_PASSWORD,
    night_date: str,
    night_team: str | None = None,
    night_action: str,
    debug: bool = True,
) -> dict[str, Any]:
    payload: dict[str, str] = {
        "action": "gwd_update_game_night",
        "admin_password": admin_password,
        "night_date": night_date,
        "night_action": night_action,
    }
    if night_team:
        payload["night_team"] = night_team
    if debug:
        payload["gwd_debug"] = "1"
    return _post(payload)


def trigger_cron(secret: str = CRON_SECRET, *, debug: bool = True) -> dict[str, Any]:
    params = {"action": "gwd_cron_run", "secret": secret}
    if debug:
        params["gwd_debug"] = "1"
    query = urllib.parse.urlencode(params)
    url = f"{urls.ADMIN_AJAX}?{query}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=20.0) as resp:
        body = resp.read().decode()
    return {"success": resp.getcode() == 200, "raw": body}


def get_debug_emails(admin_password: str = ADMIN_PASSWORD) -> dict[str, Any]:
    return _post(
        {
            "action": "gwd_debug_emails",
            "admin_password": admin_password,
            "gwd_debug": "1",
        }
    )


def clear_debug_emails(admin_password: str = ADMIN_PASSWORD) -> dict[str, Any]:
    return fetch_game_nights(admin_password=admin_password, debug=True, debug_clear=True)


def debug_availability(date_iso: str) -> dict[str, Any]:
    payload: dict[str, str] = {
        "action": "gwd_debug_availability",
        "date": date_iso,
        "gwd_debug": "1",
    }
    return _post(payload)

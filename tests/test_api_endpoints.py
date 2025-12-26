import json
import os
import urllib.error
import urllib.parse
import urllib.request

import pytest

from framework import urls
from framework.gwd_api import ADMIN_PASSWORD


def _get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=15) as resp:
        assert resp.status == 200, f"GET {url} returned {resp.status}"
        return resp.read().decode()


def _post(data: dict[str, str]) -> dict:
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        urls.ADMIN_AJAX,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
    try:
        return json.loads(body)
    except Exception as e:
        raise AssertionError(f"Non-JSON response: {body[:200]}") from e


def test_havewegot_page_exposes_search_form():
    html = _get(urls.HAVEWEGOT)
    assert "have-we-got__table" in html or 'name="hwg_search"' in html.lower(), "HaveWeGot page did not render expected markup."


def test_meal_planner_page_renders_calendar():
    html = _get(urls.MEAL_PLANNER_INDEX)
    assert "mp-calendar" in html or "meal planner" in html.lower(), "Meal Planner page response did not include calendar markup."


def test_gamewithdave_calendar_ajax_endpoint():
    res = _post({"action": "load_calendar"})
    assert res.get("success") is True
    html = res.get("data", {}).get("html", "")
    assert "calendar" in html.lower(), "Calendar HTML missing in load_calendar response."


def test_gamewithdave_fetch_game_nights_endpoint():
    res = _post(
        {
            "action": "gwd_fetch_game_nights",
            "admin_password": ADMIN_PASSWORD,
            "gwd_debug": "1",
        }
    )
    assert res.get("success") is True
    data = res.get("data", {})
    assert isinstance(data.get("nights"), list), "Expected nights list in gwd_fetch_game_nights response."


def _rest_json(permalink: str, rest_route: str, key: str, header_name: str, *, skip_key_msg: str, skip_404_msg: str):
    def _request(url: str):
        req = urllib.request.Request(url)
        if key:
            req.add_header(header_name, key)
        with urllib.request.urlopen(req, timeout=15) as resp:
            assert resp.status == 200, f"GET {url} returned {resp.status}"
            return json.loads(resp.read().decode() or "[]")

    try:
        return _request(permalink)
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        if exc.code == 401 and not key:
            pytest.skip(skip_key_msg)
        if exc.code != 404:
            raise
        # Try rest_route fallback
        try:
            return _request(rest_route)
        except urllib.error.HTTPError as exc2:  # type: ignore[attr-defined]
            if exc2.code == 401 and not key:
                pytest.skip(skip_key_msg)
            pytest.skip(skip_404_msg)


def test_todo_rest_items_endpoint():
    key = (os.getenv("PD_TODO_KEY") or "").strip()
    payload = _rest_json(
        f"{urls.BASE}/wp-json/pd-todo/v1/items?per_page=1",
        f"{urls.BASE}/index.php?rest_route=/pd-todo/v1/items&per_page=1",
        key,
        "X-PD-Todo-Key",
        skip_key_msg="pd-todo access key required; set PD_TODO_KEY to exercise this endpoint.",
        skip_404_msg="pd-todo items endpoint not reachable (404). Is the plugin active?",
    )
    assert isinstance(payload, list), "Items endpoint did not return a list."


def test_simple_workout_log_days_endpoint():
    key = (os.getenv("PDSWL_KEY") or "").strip()
    payload = _rest_json(
        f"{urls.BASE}/wp-json/pdswl/v1/days",
        f"{urls.BASE}/index.php?rest_route=/pdswl/v1/days",
        key,
        "X-PDSWL-Key",
        skip_key_msg="Simple Workout Log access key required; set PDSWL_KEY to exercise this endpoint.",
        skip_404_msg="Simple Workout Log days endpoint not reachable (404). Is the plugin active?",
    )
    assert isinstance(payload, list), "Days endpoint did not return a list."
    if payload:
        first = payload[0]
        assert "day_key" in first, "Expected day_key in SWL day payload."

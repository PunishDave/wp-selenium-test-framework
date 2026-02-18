import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

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
    assert "calendar-game-time" in html, "Calendar game time note missing in load_calendar response."


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
    nights = data.get("nights")
    assert isinstance(nights, list), "Expected nights list in gwd_fetch_game_nights response."
    for night in nights:
        assert "team" in night, "Expected team in gwd_fetch_game_nights entries."
        assert "teamLabel" in night, "Expected teamLabel in gwd_fetch_game_nights entries."


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


def _rest_json_body(method: str, permalink: str, rest_route: str, body: dict, headers: dict[str, str], *, skip_key_msg: str, skip_404_msg: str):
    payload = json.dumps(body).encode()

    def _request(url: str):
        req = urllib.request.Request(url, data=payload, method=method)
        for k, v in headers.items():
            req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status not in (200, 201):
                raise AssertionError(f"{method} {url} returned {resp.status}")
            return json.loads(resp.read().decode() or "{}")

    try:
        return _request(permalink)
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        if exc.code == 401 and "X-MP-Key" in headers and not headers.get("X-MP-Key"):
            pytest.skip(skip_key_msg)
        if exc.code != 404:
            raise
        try:
            return _request(rest_route)
        except urllib.error.HTTPError as exc2:  # type: ignore[attr-defined]
            if exc2.code == 401 and "X-MP-Key" in headers and not headers.get("X-MP-Key"):
                pytest.skip(skip_key_msg)
            pytest.skip(skip_404_msg)


def _next_saturday() -> date:
    today = date.today()
    # weekday: Monday=0 ... Sunday=6; Saturday=5
    days_ahead = (5 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


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
    if not payload:
        return

    first = payload[0]
    assert "day_key" in first, "Expected day_key in SWL day payload."
    day_key = first["day_key"]

    detail = _rest_json(
        f"{urls.BASE}/wp-json/pdswl/v1/days/{day_key}",
        f"{urls.BASE}/index.php?rest_route=/pdswl/v1/days/{day_key}",
        key,
        "X-PDSWL-Key",
        skip_key_msg="Simple Workout Log access key required; set PDSWL_KEY to exercise this endpoint.",
        skip_404_msg="Simple Workout Log day endpoint not reachable (404). Is the plugin active?",
    )
    assert isinstance(detail, dict), "Day detail endpoint did not return an object."
    workouts = detail.get("workouts", [])
    assert isinstance(workouts, list), "Day detail missing workouts list."
    if workouts:
        for w in workouts:
            assert "name" in w, "Workout missing name in day detail."
            assert "reps" in w, "Workout missing reps in day detail."
            assert "last_weight" in w, "Workout missing last_weight in day detail."
            assert "last_reps" in w, "Workout missing last_reps in day detail."
            assert "last_performed_on" in w, "Workout missing last_performed_on in day detail."


def test_meal_planner_shopping_list_get_endpoint():
    week_start = _next_saturday().isoformat()
    payload = _rest_json(
        f"{urls.BASE}/wp-json/meal-planner/v1/shopping-list?week_start={week_start}",
        f"{urls.BASE}/index.php?rest_route=/meal-planner/v1/shopping-list&week_start={week_start}",
        "",
        "X-MP-Key",
        skip_key_msg="Meal Planner access key required; set MP_KEY to exercise POST endpoints.",
        skip_404_msg="Meal Planner shopping list endpoint not reachable (404). Is the plugin active?",
    )
    assert isinstance(payload, dict), "Shopping list GET did not return an object."
    assert payload.get("week_start") == week_start, "Shopping list GET returned unexpected week_start."
    assert isinstance(payload.get("shopping_list", []), list), "shopping_list should be a list."


def test_meal_planner_shopping_list_post_endpoint():
    key = (os.getenv("MP_KEY") or os.getenv("MP_ACCESS_KEY") or "").strip()
    if not key:
        pytest.skip("Set MP_KEY or MP_ACCESS_KEY to exercise Meal Planner shopping list POST.")

    week_start = _next_saturday().isoformat()
    token = f"SeleniumItem-{int(os.getenv('PYTEST_CURRENT_TEST', '0').split(' ')[0].__hash__())}"
    items = [token, "Eggs (Test Meal)"]

    payload = _rest_json_body(
        "POST",
        f"{urls.BASE}/wp-json/meal-planner/v1/shopping-list",
        f"{urls.BASE}/index.php?rest_route=/meal-planner/v1/shopping-list",
        {"week_start": week_start, "items": items},
        {"Content-Type": "application/json", "X-MP-Key": key},
        skip_key_msg="Meal Planner access key required; set MP_KEY or MP_ACCESS_KEY to exercise this endpoint.",
        skip_404_msg="Meal Planner shopping list endpoint not reachable (404). Is the plugin active?",
    )

    assert isinstance(payload, dict), "Shopping list POST did not return an object."
    assert payload.get("week_start") == week_start, "Shopping list POST returned unexpected week_start."
    saved_items = payload.get("shopping_list", [])
    assert isinstance(saved_items, list), "shopping_list should be a list."
    assert any(token in s for s in saved_items), "Shopping list POST response missing the test token item."


def test_meal_planner_next_week_save_logs_debug_email():
    key = (os.getenv("MP_KEY") or os.getenv("MP_ACCESS_KEY") or "").strip()
    headers = {"Content-Type": "application/json", "X-MP-Key": key}

    debug_endpoint = f"{urls.BASE}/wp-json/meal-planner/v1/debug-emails"
    debug_fallback = f"{urls.BASE}/index.php?rest_route=/meal-planner/v1/debug-emails"
    clear_endpoint = f"{urls.BASE}/wp-json/meal-planner/v1/debug-emails/clear"
    clear_fallback = f"{urls.BASE}/index.php?rest_route=/meal-planner/v1/debug-emails/clear"

    try:
        _rest_json_body(
            "POST",
            clear_endpoint,
            clear_fallback,
            {},
            headers,
            skip_key_msg="Meal Planner access key required; set MP_KEY or MP_ACCESS_KEY to use debug email endpoints.",
            skip_404_msg="Meal Planner debug email clear endpoint not reachable (404). Is the plugin active?",
        )
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        if exc.code == 403:
            pytest.skip("Meal Planner debug email endpoint is disabled (non-development environment).")
        raise

    week_start = _next_saturday().isoformat()
    meals = {
        str(i): {
            "id": 0,
            "title": f"Selenium Meal {i + 1}",
            "ingredients": [f"Ingredient {i + 1}"],
        }
        for i in range(7)
    }

    _rest_json_body(
        "POST",
        f"{urls.BASE}/wp-json/meal-planner/v1/weeks",
        f"{urls.BASE}/index.php?rest_route=/meal-planner/v1/weeks",
        {"week_start": week_start, "meals": meals},
        headers,
        skip_key_msg="Meal Planner access key required; set MP_KEY or MP_ACCESS_KEY to save weeks.",
        skip_404_msg="Meal Planner weeks endpoint not reachable (404). Is the plugin active?",
    )

    debug_payload = _rest_json(
        debug_endpoint,
        debug_fallback,
        key,
        "X-MP-Key",
        skip_key_msg="Meal Planner access key required; set MP_KEY or MP_ACCESS_KEY to read debug email logs.",
        skip_404_msg="Meal Planner debug email endpoint not reachable (404). Is the plugin active?",
    )
    assert isinstance(debug_payload, dict), "Debug email endpoint did not return an object."
    entries = debug_payload.get("entries", [])
    assert isinstance(entries, list), "Debug email payload missing entries list."

    matched = None
    for entry in entries:
        if entry.get("type") == "next-week-saved" and entry.get("week_start") == week_start:
            matched = entry
            break

    assert matched is not None, f"Expected a next-week-saved debug email entry for {week_start}."
    assert matched.get("debug") is True, "Expected debug email entry to be flagged as debug mode."

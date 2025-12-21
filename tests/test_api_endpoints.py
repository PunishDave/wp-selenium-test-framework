import json
import urllib.parse
import urllib.request

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

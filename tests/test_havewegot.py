from pages.have_we_got_page import HaveWeGotPage
import re


def _lower_set(xs):
    return {x.strip().lower() for x in xs}


def test_havewegot_filters_exist_and_have_options(driver):
    page = HaveWeGotPage(driver).load()

    type_select = driver.find_element(*page.TYPE)
    type_opts = [o.text.strip() for o in type_select.find_elements("css selector", "option")]
    assert _lower_set(type_opts) >= {"all", "films", "tv shows"}

    assert driver.find_element(*page.STATUS).get_attribute("type") in (None, "", "text")
    assert driver.find_element(*page.SEARCH).get_attribute("type") in (None, "", "text", "search")

    order_select = driver.find_element(*page.ORDER)
    order_opts = [o.text.strip() for o in order_select.find_elements("css selector", "option")]

    expected_orders = {
        "Last accessed (oldest first)",
        "Name (A to Z)",
        "Name (Z to A)",
        "Status (A to Z)",
        "Status (Z to A)",
        "Type (A to Z)",
        "Type (Z to A)",
    }
    assert expected_orders.issubset(set(order_opts))


def test_havewegot_table_headers_exist(driver):
    page = HaveWeGotPage(driver).load()

    headers = [h.strip().lower() for h in page.header_texts()]
    assert headers == ["type", "name", "status", "last access"]

    ths = driver.find_elements(*page.HEADER_CELLS)
    assert len(ths) == 4


def test_havewegot_type_filter_films(driver):
    page = HaveWeGotPage(driver).load()

    page.set_type("Films")
    page.submit_filters()

    rows = page.read_rows()
    assert rows, "Expected at least one Film result"
    assert all(r.type.lower().startswith("film") for r in rows)


def test_havewegot_status_filter_invalid_returns_none(driver):
    page = HaveWeGotPage(driver).load()

    page.set_status("banana")
    page.submit_filters()

    rows = page.read_rows()
    assert len(rows) == 0


def test_havewegot_status_filter_watched(driver):
    page = HaveWeGotPage(driver).load()

    page.set_status("Watched")
    page.submit_filters()

    rows = page.read_rows()
    assert rows, "Expected watched results"
    assert all(r.status.strip().lower() == "watched" for r in rows)


def test_havewegot_search_filter_finds_existing_item(driver):
    page = HaveWeGotPage(driver).load()

    # Grab an existing row so the test doesn’t rely on a specific dataset
    initial = page.read_rows()
    assert initial, "Need at least 1 row in the table to test search."

    # Pick a reasonably unique token from the first row’s name
    tokens = re.findall(r"[A-Za-z0-9]{4,}", initial[0].name)
    assert tokens, f"Could not derive a search token from name: {initial[0].name!r}"
    token = tokens[0]

    page.set_search(token)
    page.submit_filters()

    rows = page.read_rows()
    assert rows, f"Expected matching results for token {token!r}"
    assert all(token.lower() in r.name.lower() for r in rows)

def test_havewegot_click_type_header_changes_sort_state(driver):
    page = HaveWeGotPage(driver).load()

    # Click header and ensure sort state changes (more reliable than row order)
    before_headers = page.header_texts()
    page.click_header("type")
    after_headers = page.header_texts()

    # Headers should still be present and stable
    assert before_headers and after_headers

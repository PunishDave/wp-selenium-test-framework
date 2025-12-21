from pages.home_page import HomePage


def test_homepage_menu_contains_expected_items(driver):
    page = HomePage(driver).load()

    expected = {"Home", "Blog", "Gear", "Quotes", "GameWithDave"}
    actual = set(page.menu_texts())

    missing = expected - actual
    assert not missing, f"Missing menu item(s): {sorted(missing)}. Actual: {sorted(actual)}"


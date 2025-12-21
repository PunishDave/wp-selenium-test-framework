# tests/test_meal_planner_admin.py

import os
import time

from pages.wp_admin_login_page import WpAdminLoginPage
from pages.wp_admin_meal_planner_recipes_page import WpAdminMealPlannerRecipesPage


def _get_admin_creds() -> tuple[str, str]:
    user = (os.getenv("WP_ADMIN_USER") or "").strip()
    pw = (os.getenv("WP_ADMIN_PASS") or "").strip()
    assert user and pw, "WP_ADMIN_USER / WP_ADMIN_PASS not set."
    return user, pw


def test_wp_admin_meal_planner_recipes_and_add_new(driver):
    user, pw = _get_admin_creds()
    WpAdminLoginPage(driver).load().login(user, pw)

    page = WpAdminMealPlannerRecipesPage(driver).open_recipes()
    page.assert_has_some_recipes()

    page.click_add_new()

    title = f"Selenium Test Recipe {int(time.time())}"
    ingredients = "Test Ingredient 1\nTest Ingredient 2\nTest Ingredient 3"
    page.add_recipe(title, ingredients)


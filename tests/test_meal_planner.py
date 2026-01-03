# tests/test_meal_planner.py

from pages.meal_planner_page import MealPlannerPage


def test_meal_planner_current_and_next_week_render(driver):
    page = MealPlannerPage(driver).load()
    page.set_access_key_if_available()
    page.assert_current_and_next_week_present()


def test_meal_planner_generate_replace_override_and_optional_save(driver):
    page = MealPlannerPage(driver).load()
    page.set_access_key_if_available()

    page.click_generate_week()
    page.wait_until_cells_filled(min_cells=7)

    page.click_replace_day0_and_wait_change()
    page.override_day0_with_first_meal()

    # save is optional / may be unavailable
    page.save_week_if_possible()

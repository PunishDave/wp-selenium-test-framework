# pages/wp_admin_meal_planner_recipes_page.py

from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from framework.urls import WP_ADMIN


class WpAdminMealPlannerRecipesPage:
    # Your confirmed URL
    RECIPES_URL = "admin.php?page=mp_recipes"
    ADD_URL     = "admin.php?page=mp_add_recipe"

    # More flexible locators
    ADD_NEW = (By.CSS_SELECTOR, f"a.page-title-action[href='{ADD_URL}'], a[href='{ADD_URL}']")
    ANY_TABLE = (By.CSS_SELECTOR, "table")
    WP_LIST_TABLE = (By.CSS_SELECTOR, "table.wp-list-table")
    ANY_TBODY_ROWS = (By.CSS_SELECTOR, "table tbody tr")

    TITLE = (By.ID, "title")
    INGREDIENTS = (By.ID, "ingredients")
    SUBMIT = (By.CSS_SELECTOR, "input[name='submit']")
    NOTICE = (By.CSS_SELECTOR, ".notice, .updated, .error")

    def __init__(self, driver):
        self.driver = driver

    def open_recipes(self):
        url = f"{WP_ADMIN.rstrip('/')}/{self.RECIPES_URL}"
        self.driver.get(url)

        def page_ready(d):
            # Any of these implies we are on the recipes/admin screen
            if d.find_elements(*self.ADD_NEW):
                return True
            if d.find_elements(*self.WP_LIST_TABLE):
                return True
            if d.find_elements(*self.ANY_TABLE):
                return True
            return False

        WebDriverWait(self.driver, 25).until(page_ready)
        return self

    def assert_has_some_recipes(self):
        # We only need "some rows exist somewhere in a table body"
        rows = self.driver.find_elements(*self.ANY_TBODY_ROWS)
        assert rows, "Expected at least one recipe row in a table on the Meal Planner recipes admin page."
        return self

    def click_add_new(self):
        WebDriverWait(self.driver, 25).until(EC.element_to_be_clickable(self.ADD_NEW)).click()
        WebDriverWait(self.driver, 25).until(EC.presence_of_element_located(self.TITLE))
        return self

    def add_recipe(self, title: str, ingredients: str):
        title_el = self.driver.find_element(*self.TITLE)
        title_el.clear()
        title_el.send_keys(title)

        ing_el = self.driver.find_element(*self.INGREDIENTS)
        ing_el.clear()
        ing_el.send_keys(ingredients)

        self.driver.find_element(*self.SUBMIT).click()

        def notice_has_text(d):
            notices = d.find_elements(*self.NOTICE)
            blob = "\n".join((n.text or "") for n in notices).lower()
            return "recipe added" in blob

        WebDriverWait(self.driver, 25).until(notice_has_text)
        return self


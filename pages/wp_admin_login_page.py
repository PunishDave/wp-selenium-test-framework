from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from framework.urls import WP_ADMIN


class WpAdminLoginPage:
    URL = WP_ADMIN

    USER = (By.ID, "user_login")
    PASS = (By.ID, "user_pass")
    SUBMIT = (By.ID, "wp-submit")

    WELCOME_PANEL = (By.CSS_SELECTOR, "div.welcome-panel-content h2")

    def __init__(self, driver):
        self.driver = driver

    def load(self):
        self.driver.get(self.URL)
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(self.USER))
        return self

    def login(self, username: str, password: str):
        self.driver.find_element(*self.USER).clear()
        self.driver.find_element(*self.USER).send_keys(username)

        self.driver.find_element(*self.PASS).clear()
        self.driver.find_element(*self.PASS).send_keys(password)

        self.driver.find_element(*self.SUBMIT).click()

        # confirm login by welcome panel heading
        WebDriverWait(self.driver, 25).until(
            EC.text_to_be_present_in_element(self.WELCOME_PANEL, "Welcome to WordPress!")
        )
        return self


from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from framework.urls import HOME


class HomePage:
    URL = HOME

    MENU = (By.CSS_SELECTOR, "ul#menu-menu")
    MENU_LINKS = (By.CSS_SELECTOR, "ul#menu-menu a")

    def __init__(self, driver):
        self.driver = driver

    def load(self):
        self.driver.get(self.URL)
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(self.MENU))
        return self

    def menu_texts(self) -> list[str]:
        links = self.driver.find_elements(*self.MENU_LINKS)
        return [a.text.strip() for a in links if a.text and a.text.strip()]


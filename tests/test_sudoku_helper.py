from __future__ import annotations

import json

import pytest
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.sudoku_helper_page import SudokuHelperPage


def test_sudoku_helper_renders_grid_and_controls(driver):
    page = SudokuHelperPage(driver).load()

    assert page.cell_count() == 81, "Expected a 9x9 Sudoku grid (81 cells)."
    wait = WebDriverWait(driver, 5)
    wait.until(EC.visibility_of_element_located(page.LOAD_BUTTON))
    wait.until(EC.visibility_of_element_located(page.SAVE_BUTTON))
    wait.until(EC.visibility_of_element_located(page.GENERATE_BUTTON))
    wait.until(EC.visibility_of_element_located(page.NOTES_TOGGLE))


def test_sudoku_helper_numpad_enters_value_in_selected_cell(driver):
    page = SudokuHelperPage(driver).load()

    page.click_cell(1, 1).click_numpad(5)

    assert page.cell_value(1, 1) == "5"


def test_sudoku_helper_generate_creates_givens(driver):
    page = SudokuHelperPage(driver).load()

    page.click_generate().wait_for_generated(timeout=60)

    filled = page.filled_count()
    locked = page.locked_count()
    assert filled >= 20, f"Expected generated puzzle to populate some cells, got {filled}"
    assert locked >= 20, f"Expected generated givens to be locked, got {locked}"
    assert locked <= filled


def test_sudoku_helper_load_button_shows_pressed_feedback(driver):
    page = SudokuHelperPage(driver).load()

    before = page.load_button_text()
    page.click_load()

    assert page.load_button_is_pending(), "Expected Load button to enter pending/pressed state."
    after = page.load_button_text()
    assert after and after != before
    assert "choose file" in after.lower()


def test_sudoku_helper_loads_valid_save_file(driver, tmp_path):
    page = SudokuHelperPage(driver).load()

    grid = [0] * 81
    grid[0] = 5      # r1c1
    grid[10] = 3     # r2c2
    grid[80] = 9     # r9c9

    notes = [[] for _ in range(81)]
    notes[1] = [1, 2, 9]  # r1c2 (left empty to preserve notes)

    givens = [False] * 81
    givens[0] = True
    givens[10] = True

    payload = {
        "app": "pd-sudoku-helper",
        "version": 1,
        "label": "Selenium Sudoku Smoke",
        "grid": grid,
        "notes": notes,
        "givens": givens,
    }

    save_file = tmp_path / "selenium-sudoku-smoke.pdsudoku"
    save_file.write_text(json.dumps(payload), encoding="utf-8")

    page.upload_save_file(str(save_file)).wait_for_status_contains("Puzzle loaded.", timeout=8)

    assert page.cell_value(1, 1) == "5"
    assert page.cell_value(2, 2) == "3"
    assert page.cell_value(9, 9) == "9"
    assert page.cell_is_locked(1, 1)
    assert page.cell_is_locked(2, 2)
    assert not page.cell_is_locked(9, 9)
    assert page.puzzle_name_value() == "Selenium Sudoku Smoke"


@pytest.mark.consent_manual
def test_sudoku_helper_has_no_cookie_banner_or_gtm(driver, cookie_consent):
    page = SudokuHelperPage(driver).load()

    driver.delete_all_cookies()
    page.refresh()

    assert not cookie_consent.wait_for_banner_visible(timeout=3), "Cookie banner should not appear on Sudoku Helper."
    assert not cookie_consent.banner_visible(), "Cookie banner should not be visible on Sudoku Helper."
    assert not cookie_consent.gtm_present(), "GTM should not be present on Sudoku Helper."

    source = (driver.page_source or "").lower()
    assert "googletagmanager.com" not in source

import os

BASE = os.getenv("WP_BASE_URL", "http://localhost:8080").rstrip("/")

HOME = f"{BASE}/"

# WordPress (no pretty permalinks)
WP_FRONT = f"{BASE}/index.php"
HAVEWEGOT = f"{BASE}/?page_id=21"

# GameWithDave (front-end)
GAME_WITH_DAVE_PRETTY = f"{BASE}/gamewithdave/"
GAME_WITH_DAVE_INDEX  = f"{WP_FRONT}/gamewithdave/"
GAME_WITH_DAVE_PAGE_ID = f"{BASE}/?page_id=15"

# WP Admin
WP_ADMIN = f"{BASE}/wp-admin/"
ADMIN_AJAX = f"{WP_ADMIN}admin-ajax.php"

# Meal Planner (front-end)
MEAL_PLANNER_PRETTY = f"{BASE}/meal-planner/"
MEAL_PLANNER_INDEX  = f"{BASE}/?page_id=29"

# To-Do (front-end)
TODO_PRETTY = f"{BASE}/to-do/"
TODO_INDEX  = f"{BASE}/?page_id=33"

# Simple Workout Log (front-end)
WORKOUT_LOG_PRETTY = f"{BASE}/workout-log/"
WORKOUT_LOG_INDEX  = f"{BASE}/?page_id=35"

# House Log (front-end)
HOUSE_LOG_PRETTY = f"{BASE}/house-log/"
HOUSE_LOG_INDEX  = f"{BASE}/?page_id=25"

# Sudoku Helper (front-end)
SUDOKU_HELPER_PRETTY = f"{BASE}/sudoku-helper/"
SUDOKU_HELPER_INDEX  = f"{BASE}/?page_id=6"

# WP Admin slugs (stable if you know them)
MP_ADMIN_RECIPES_SLUG = "admin.php?page=mp_recipes"
MP_ADMIN_ADD_SLUG     = "admin.php?page=mp_add_recipe"

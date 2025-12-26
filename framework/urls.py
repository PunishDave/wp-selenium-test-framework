BASE = "http://localhost"

HOME = f"{BASE}/"

# WordPress (no pretty permalinks)
WP_FRONT = f"{BASE}/index.php"
HAVEWEGOT = f"{WP_FRONT}/havewegot/"

# GameWithDave (front-end)
GAME_WITH_DAVE_PRETTY = f"{BASE}/gamewithdave/"
GAME_WITH_DAVE_INDEX  = f"{WP_FRONT}/gamewithdave/"

# WP Admin
WP_ADMIN = f"{BASE}/wp-admin/"
ADMIN_AJAX = f"{WP_ADMIN}admin-ajax.php"

# Meal Planner (front-end)
MEAL_PLANNER_PRETTY = f"{BASE}/meal-planner/"
MEAL_PLANNER_INDEX  = f"{BASE}/index.php/meal-planner/"

# To-Do (front-end)
TODO_PRETTY = f"{BASE}/to-do/"
TODO_INDEX  = f"{BASE}/index.php/to-do/"

# Simple Workout Log (front-end)
WORKOUT_LOG_PRETTY = f"{BASE}/workout-log/"
WORKOUT_LOG_INDEX  = f"{BASE}/index.php/workout-log/"

# WP Admin slugs (stable if you know them)
MP_ADMIN_RECIPES_SLUG = "admin.php?page=mp_recipes"
MP_ADMIN_ADD_SLUG     = "admin.php?page=mp_add_recipe"

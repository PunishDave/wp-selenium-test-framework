## Running the tests
- Set any needed environment variables, including `WP_BASE_URL` when WordPress is not at `http://localhost:8080`, `WP_ADMIN_USER`, `WP_ADMIN_PASS`, and `HEADLESS=true` for headless Chrome.
- Set `GWD_ACCESS_KEY` to the key configured under WordPress Admin > GameWithDave > HomeApps API when running the GameWithDave REST and notification coverage.
- From the repo root, run `pytest -q` or use `python -m gui.test_runner_tk` for the GUI runner.

## Reports
- Every pytest run creates a fresh folder under `reports/` named with the current timestamp.
- The folder contains `report.html` (human-friendly) and `report.json` plus any screenshots captured at the end of each test that uses the `driver` fixture.
- The HTML report path is printed in the pytest summary; open it in a browser to review pass/fail status and screenshots.

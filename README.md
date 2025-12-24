## Running the tests
- Set any needed environment variables (e.g., `WP_ADMIN_USER`, `WP_ADMIN_PASS`, optionally `MP_PASSWORD`, and `HEADLESS=true` if you want headless Chrome).
- From the repo root, run `pytest -q` or use `python -m gui.test_runner_tk` for the GUI runner.

## Reports
- Every pytest run creates a fresh folder under `reports/` named with the current timestamp.
- The folder contains `report.html` (human-friendly) and `report.json` plus any screenshots captured at the end of each test that uses the `driver` fixture.
- The HTML report path is printed in the pytest summary; open it in a browser to review pass/fail status and screenshots.

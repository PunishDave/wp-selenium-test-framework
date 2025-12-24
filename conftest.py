import pytest
from framework.config import get_settings
from framework.driver import make_driver
from framework.reporting import TestRunReporter


@pytest.fixture
def driver():
    settings = get_settings()

    driver = make_driver(headless=settings.headless)
    try:
        yield driver
    finally:
        driver.quit()


def pytest_configure(config):
    # Create a reporter for this run so we can collect results/screenshots.
    config._wp_reporter = TestRunReporter()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    reporter: TestRunReporter | None = getattr(item.config, "_wp_reporter", None)
    if reporter is None:
        return

    if rep.when == "call" or (rep.when == "setup" and rep.outcome in {"failed", "skipped"}) or (rep.when == "teardown" and rep.outcome == "failed"):
        driver = item.funcargs.get("driver")
        reporter.record(item, rep, driver, stage=rep.when)


def pytest_sessionfinish(session, exitstatus):
    reporter: TestRunReporter | None = getattr(session.config, "_wp_reporter", None)
    if reporter:
        reporter.finalize()


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    reporter: TestRunReporter | None = getattr(config, "_wp_reporter", None)
    if reporter and reporter.report_path:
        terminalreporter.write_sep("-", f"HTML report: {reporter.report_path}")

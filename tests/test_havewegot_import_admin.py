import os
from pathlib import Path

from pages.wp_admin_login_page import WpAdminLoginPage
from pages.have_we_got_import_admin_page import HaveWeGotImportAdminPage


TESTS_DIR = Path(__file__).resolve().parent
VALID_XML = str(TESTS_DIR / "media_access_valid.xml")
INVALID_XML = str(TESTS_DIR / "media_access_invalid.xml")


def _get_admin_creds() -> tuple[str, str]:
    user = os.getenv("WP_ADMIN_USER", "").strip()
    pw = os.getenv("WP_ADMIN_PASS", "").strip()
    assert user and pw, "WP_ADMIN_USER / WP_ADMIN_PASS not set (set them in GUI or export in shell)."
    return user, pw


def test_havewegot_import_valid_xml(driver):
    user, pw = _get_admin_creds()

    WpAdminLoginPage(driver).load().login(user, pw)

    page = HaveWeGotImportAdminPage(driver).open()
    page.upload_and_import(VALID_XML)

    page.wait_for_text("Import complete. 4 added, 0 updated.")


def test_havewegot_import_invalid_xml(driver):
    user, pw = _get_admin_creds()

    WpAdminLoginPage(driver).load().login(user, pw)

    page = HaveWeGotImportAdminPage(driver).open()
    page.upload_and_import(INVALID_XML)

    page.wait_for_text("Could not parse XML file.")


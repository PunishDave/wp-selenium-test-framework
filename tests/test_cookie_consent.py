from __future__ import annotations

from framework import urls

import pytest


@pytest.mark.consent_manual
def test_cookie_banner_visible_without_saved_choice(driver, cookie_consent):
    driver.get(urls.HOME)
    driver.delete_all_cookies()
    driver.refresh()

    assert cookie_consent.wait_for_banner_visible(timeout=6), "Expected cookie banner to be visible with no saved consent."


@pytest.mark.consent_manual
def test_reject_removes_gtm_and_persists_across_pages(driver, cookie_consent):
    driver.get(urls.HOME)
    driver.delete_all_cookies()
    driver.refresh()

    assert cookie_consent.wait_for_banner_visible(timeout=6), "Expected cookie banner before rejecting consent."
    assert cookie_consent.choose("reject", timeout=6), "Failed to click reject on cookie banner."
    assert cookie_consent.wait_for_banner_hidden(timeout=6), "Cookie banner should hide after rejection."
    assert not cookie_consent.gtm_present(), "GTM should not be present after rejecting consent."

    cookie_value = driver.execute_script("return (document.cookie || '').toString();")
    assert "pd_cookie_consent=reject" in cookie_value, f"Expected reject cookie, got: {cookie_value!r}"

    driver.get(urls.HAVEWEGOT)
    assert not cookie_consent.gtm_present(), "GTM should remain absent on subsequent pages after rejection."


@pytest.mark.consent_manual
def test_accept_loads_gtm_and_persists_across_pages(driver, cookie_consent):
    driver.get(urls.HOME)
    driver.delete_all_cookies()
    driver.refresh()

    assert cookie_consent.wait_for_banner_visible(timeout=6), "Expected cookie banner before accepting consent."
    assert cookie_consent.choose("accept", timeout=6), "Failed to click accept on cookie banner."
    assert cookie_consent.wait_for_banner_hidden(timeout=6), "Cookie banner should hide after acceptance."

    assert cookie_consent.gtm_present(), "GTM should be present after accepting consent."

    cookie_value = driver.execute_script("return (document.cookie || '').toString();")
    assert "pd_cookie_consent=accept" in cookie_value, f"Expected accept cookie, got: {cookie_value!r}"

    driver.get(urls.HAVEWEGOT)
    assert cookie_consent.gtm_present(), "GTM should remain present on subsequent pages after acceptance."

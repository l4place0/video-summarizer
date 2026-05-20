"""Playwright test: verify retry button is visible for failed tasks."""

import pytest

BASE = "http://127.0.0.1:8000"


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        yield br
        br.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context()
    p = ctx.new_page()
    yield p
    p.close()


def test_retry_button_visible_for_failed_task(page):
    """Retry button should appear when viewing a failed task."""
    page.goto(BASE)
    page.wait_for_load_state("networkidle")

    # Go to history
    page.click('[data-page="history"]')
    page.wait_for_timeout(500)

    # Find the row with "failed" status and click its View button
    failed_row = page.locator('#history-body tr').filter(has_text='failed')
    if failed_row.count() == 0:
        pytest.skip("No failed tasks in history")

    failed_row.locator('button:has-text("View")').click()
    page.wait_for_timeout(1000)

    # Check if retry button is visible
    retry_btn = page.locator('#retry-task-btn')
    assert retry_btn.is_visible(), "Retry button should be visible for failed tasks"

    # Check error message is shown
    error_el = page.locator('#result-error')
    assert error_el.is_visible(), "Error message should be visible"
    error_text = error_el.inner_text()
    assert len(error_text) > 0, "Error message should not be empty"


def test_retry_button_hidden_for_done_task(page):
    """Retry button should NOT appear for completed tasks."""
    page.goto(BASE)
    page.wait_for_load_state("networkidle")

    page.click('[data-page="history"]')
    page.wait_for_timeout(500)

    # Find a done row
    done_row = page.locator('#history-body tr').filter(has_text='done')
    if done_row.count() == 0:
        pytest.skip("No done tasks in history")

    done_row.first.locator('button:has-text("View")').click()
    page.wait_for_timeout(1000)

    retry_btn = page.locator('#retry-task-btn')
    assert not retry_btn.is_visible(), "Retry button should be hidden for done tasks"

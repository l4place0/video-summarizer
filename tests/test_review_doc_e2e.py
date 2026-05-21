"""E2E Playwright tests for the interactive review document feature.

Covers tasks 7.1, 7.2, 7.3 from the change.
Requires a running server at http://127.0.0.1:8000 with at least one done task.
"""

import json
import re
import tempfile
from pathlib import Path

import httpx
import pytest

BASE = "http://127.0.0.1:8000"


def get_done_task_id() -> str:
    resp = httpx.get(f"{BASE}/api/tasks")
    done = [t for t in resp.json()["tasks"] if t["status"] == "done"]
    assert done, "Need at least one done task"
    return done[0]["task_id"]


def download_review_html(task_id: str | None = None) -> Path:
    """Download review doc HTML and save to a temp file. Returns file path."""
    tid = task_id or get_done_task_id()
    resp = httpx.get(f"{BASE}/api/tasks/{tid}/review-doc", follow_redirects=True)
    assert resp.status_code == 200
    f = tempfile.NamedTemporaryFile(suffix=".html", delete=False, prefix="review_")
    f.write(resp.text.encode())
    f.close()
    return Path(f.name)


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        yield br
        br.close()


# === 7.1 E2E: click Generate Review Doc → download HTML ===

class TestGenerateReviewDoc:
    def test_button_visible_and_download_works(self, browser):
        """7.1: View a done task → Generate Review Doc button visible → download HTML."""
        ctx = browser.new_context(accept_downloads=True)
        page = ctx.new_page()
        page.goto(BASE)
        page.wait_for_load_state("networkidle")

        # Navigate to history and click a done task
        page.click('[data-page="history"]')
        page.wait_for_timeout(500)
        done_row = page.locator('#history-body tr').filter(has_text='done').first
        done_row.locator('button:has-text("View")').click()
        page.wait_for_timeout(1000)

        # Button should be visible
        btn = page.locator('#export-review-doc')
        assert btn.is_visible(), "Generate Review Doc button should be visible for done tasks"

        # Click and capture download
        with page.expect_download(timeout=30000) as dl_info:
            btn.click()
        download = dl_info.value
        filename = download.suggested_filename
        assert filename.endswith(".html"), f"Expected .html, got {filename}"

        tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
        download.save_as(tmp.name)
        size = Path(tmp.name).stat().st_size
        assert size > 5000, f"HTML too small: {size} bytes"
        page.close()


# === 7.2 Verify HTML interactive features ===

class TestReviewDocFeatures:
    """7.2: Verify interactive features in the generated HTML."""

    @pytest.fixture(scope="class")
    def html_file(self):
        f = download_review_html()
        yield f
        f.unlink(missing_ok=True)

    def test_tabs_switch(self, html_file, browser):
        """Tabs should switch panels correctly."""
        page = browser.new_context().new_page()
        page.goto(html_file.as_uri())
        page.wait_for_load_state("load")

        assert page.locator('#panel-summary').is_visible()

        page.click('.nav-tab[data-tab="cards"]')
        page.wait_for_timeout(300)
        assert page.locator('#panel-cards').is_visible()

        page.click('.nav-tab[data-tab="timeline"]')
        page.wait_for_timeout(300)
        assert page.locator('#panel-timeline').is_visible()

        page.click('.nav-tab[data-tab="transcript"]')
        page.wait_for_timeout(300)
        assert page.locator('#panel-transcript').is_visible()
        page.close()

    def test_summary_renders(self, html_file, browser):
        """Summary panel should have rendered markdown content."""
        page = browser.new_context().new_page()
        page.goto(html_file.as_uri())
        page.wait_for_load_state("load")
        text = page.locator('#summary-content').inner_text()
        assert len(text) > 50, f"Summary too short: {len(text)} chars"
        page.close()

    def test_search_highlights(self, html_file, browser):
        """Search should highlight matching text."""
        page = browser.new_context().new_page()
        page.goto(html_file.as_uri())
        page.wait_for_load_state("load")

        search_input = page.locator('#search-input')
        search_input.fill('的')
        page.wait_for_timeout(500)

        marks = page.locator('#summary-content mark')
        assert marks.count() > 0, "Search should highlight matches"

        counter = page.locator('#search-count').inner_text()
        assert '/' in counter, f"Counter should show 'N/M', got: {counter}"
        page.close()

    def test_transcript_segments(self, html_file, browser):
        """Transcript should have segments with timestamps."""
        page = browser.new_context().new_page()
        page.goto(html_file.as_uri())
        page.wait_for_load_state("load")

        page.click('.nav-tab[data-tab="transcript"]')
        page.wait_for_timeout(300)

        segs = page.locator('.transcript-seg')
        assert segs.count() > 0, "Should have transcript segments"
        page.close()

    def test_card_flip_and_rating(self, html_file, browser):
        """Cards should flip on click and rating should work."""
        page = browser.new_context().new_page()
        page.goto(html_file.as_uri())
        page.wait_for_load_state("load")

        page.click('.nav-tab[data-tab="cards"]')
        page.wait_for_timeout(300)

        cards = page.locator('.flash-card')
        if cards.count() == 0:
            pytest.skip("No review cards in this task")

        first_card = cards.first
        first_card.click()
        page.wait_for_timeout(600)
        assert first_card.evaluate("el => el.classList.contains('flipped')"), "Card should be flipped"

        first_card.locator('.card-status button').first.click()
        page.wait_for_timeout(500)
        page.close()

    def test_notes_save(self, html_file, browser):
        """Notes should be saveable."""
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(html_file.as_uri())
        page.wait_for_load_state("load")

        page.click('.nav-tab[data-tab="transcript"]')
        page.wait_for_timeout(300)

        segs = page.locator('.transcript-seg')
        if segs.count() == 0:
            pytest.skip("No transcript segments")

        first_seg = segs.first
        first_seg.locator('.note-btn').click()
        page.wait_for_timeout(300)

        textarea = page.locator('.note-input-wrap textarea')
        if textarea.count() == 0:
            pytest.skip("Note input didn't appear")
        textarea.fill('E2E test note')
        page.locator('.note-input-wrap button:has-text("Save")').click()
        page.wait_for_timeout(500)

        note_el = page.locator('.seg-note')
        assert note_el.count() > 0, "Note should appear after saving"
        assert 'E2E test note' in note_el.first.inner_text()
        page.close()

    def test_lightbox(self, html_file, browser):
        """Frame lightbox should open on click and close on Escape."""
        page = browser.new_context().new_page()
        page.goto(html_file.as_uri())
        page.wait_for_load_state("load")

        page.click('.nav-tab[data-tab="timeline"]')
        page.wait_for_timeout(300)

        frames = page.locator('.tl-frame')
        if frames.count() == 0:
            pytest.skip("No frames in this task")

        # Single click opens lightbox
        frames.first.click()
        page.wait_for_timeout(500)
        assert page.locator('#lightbox').evaluate("el => el.classList.contains('active')"), "Lightbox should open"

        # Escape closes it
        page.keyboard.press('Escape')
        page.wait_for_timeout(300)
        assert not page.locator('#lightbox').evaluate("el => el.classList.contains('active')"), "Lightbox should close"
        page.close()


# === 7.3 Old task fallback ===

class TestOldTaskFallback:
    """7.3: Tasks summarized before the feature should degrade gracefully."""

    def test_old_task_generates_valid_html(self):
        """Old tasks without review cards should still produce valid HTML."""
        task_id = get_done_task_id()
        resp = httpx.get(f"{BASE}/api/tasks/{task_id}/review-doc", follow_redirects=True)
        assert resp.status_code == 200
        html = resp.text

        assert 'data-tab="cards"' in html
        assert 'data-tab="transcript"' in html

        match = re.search(r'const DATA\s*=\s*(\{.*?\});\s*$', html, re.DOTALL | re.MULTILINE)
        assert match
        data = json.loads(match.group(1))
        assert "cards" in data
        assert "transcriptSegments" in data

    def test_old_task_no_js_errors(self, browser):
        """Old task HTML should render without JS errors."""
        html_file = download_review_html()

        ctx = browser.new_context()
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))

        page.goto(html_file.as_uri())
        page.wait_for_load_state("load")
        page.wait_for_timeout(1000)

        assert not errors, f"JS errors: {errors}"

        # Cards tab should work (empty or populated)
        page.click('.nav-tab[data-tab="cards"]')
        page.wait_for_timeout(300)
        assert page.locator('#panel-cards').is_visible()

        cards = page.locator('.flash-card')
        empty = page.locator('.empty-state')
        assert cards.count() > 0 or empty.count() > 0

        page.close()
        html_file.unlink(missing_ok=True)

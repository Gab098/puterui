"""Browser control for PuterUI.

Provides the ability to control a local browser via Selenium or
Playwright. This is optional -- the dependencies are imported lazily
so they are only needed when browser features are actually used.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class BrowserResult:
    """Result of a browser action."""

    success: bool
    data: str = ""
    error: str = ""
    url: str = ""
    title: str = ""


class BrowserController:
    """Controls a local browser for web interaction.

    Supports two backends:
    - selenium (with chromedriver)
    - playwright (async-native)

    Falls back gracefully if neither is installed.
    """

    def __init__(self) -> None:
        self._backend: Optional[str] = None
        self._driver: Any = None
        self._playwright: Any = None
        self._browser: Any = None
        self._page: Any = None

    async def start(self, backend: Optional[str] = None) -> BrowserResult:
        """Start the browser. Auto-detects available backend if not specified."""
        if backend:
            self._backend = backend
        else:
            self._backend = self._detect_backend()

        if self._backend is None:
            return BrowserResult(
                success=False,
                error=(
                    "No browser backend available. Install one of:\n"
                    "  pip install selenium webdriver-manager\n"
                    "  pip install playwright && playwright install chromium"
                ),
            )

        if self._backend == "playwright":
            return await self._start_playwright()
        elif self._backend == "selenium":
            return await self._start_selenium()
        else:
            return BrowserResult(success=False, error=f"Unknown backend: {self._backend}")

    async def navigate(self, url: str) -> BrowserResult:
        """Navigate to a URL."""
        if not self._is_running():
            return BrowserResult(success=False, error="Browser not started. Use /browser start")

        try:
            if self._backend == "playwright":
                await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
                title = await self._page.title()
                return BrowserResult(
                    success=True, url=url, title=title,
                    data=f"Navigated to: {url} -- {title}",
                )
            else:
                self._driver.get(url)
                return BrowserResult(
                    success=True, url=url, title=self._driver.title,
                    data=f"Navigated to: {url} -- {self._driver.title}",
                )
        except Exception as exc:
            return BrowserResult(success=False, error=f"Navigation failed: {exc}")

    async def get_text(self) -> BrowserResult:
        """Get the visible text content of the current page."""
        if not self._is_running():
            return BrowserResult(success=False, error="Browser not started.")

        try:
            if self._backend == "playwright":
                text = await self._page.inner_text("body")
                url = self._page.url
                title = await self._page.title()
            else:
                text = self._driver.find_element("tag name", "body").text
                url = self._driver.current_url
                title = self._driver.title

            # Truncate very long pages
            if len(text) > 15000:
                text = text[:15000] + "\n... (truncated)"

            return BrowserResult(success=True, data=text, url=url, title=title)
        except Exception as exc:
            return BrowserResult(success=False, error=f"Failed to get text: {exc}")

    async def get_html(self) -> BrowserResult:
        """Get the HTML source of the current page."""
        if not self._is_running():
            return BrowserResult(success=False, error="Browser not started.")

        try:
            if self._backend == "playwright":
                html = await self._page.content()
                url = self._page.url
            else:
                html = self._driver.page_source
                url = self._driver.current_url

            if len(html) > 50000:
                html = html[:50000] + "\n... (truncated)"

            return BrowserResult(success=True, data=html, url=url)
        except Exception as exc:
            return BrowserResult(success=False, error=f"Failed to get HTML: {exc}")

    async def click(self, selector: str) -> BrowserResult:
        """Click an element by CSS selector."""
        if not self._is_running():
            return BrowserResult(success=False, error="Browser not started.")

        try:
            if self._backend == "playwright":
                await self._page.click(selector, timeout=5000)
                await self._page.wait_for_load_state("domcontentloaded")
                title = await self._page.title()
                return BrowserResult(
                    success=True,
                    data=f"Clicked: {selector}",
                    url=self._page.url,
                    title=title,
                )
            else:
                element = self._driver.find_element("css selector", selector)
                element.click()
                return BrowserResult(
                    success=True,
                    data=f"Clicked: {selector}",
                    url=self._driver.current_url,
                    title=self._driver.title,
                )
        except Exception as exc:
            return BrowserResult(success=False, error=f"Click failed: {exc}")

    async def type_text(self, selector: str, text: str) -> BrowserResult:
        """Type text into an element."""
        if not self._is_running():
            return BrowserResult(success=False, error="Browser not started.")

        try:
            if self._backend == "playwright":
                await self._page.fill(selector, text, timeout=5000)
            else:
                element = self._driver.find_element("css selector", selector)
                element.clear()
                element.send_keys(text)

            return BrowserResult(
                success=True,
                data=f"Typed into {selector}: {text[:50]}{'...' if len(text) > 50 else ''}",
            )
        except Exception as exc:
            return BrowserResult(success=False, error=f"Type failed: {exc}")

    async def screenshot(self, path: Optional[str] = None) -> BrowserResult:
        """Take a screenshot of the current page."""
        if not self._is_running():
            return BrowserResult(success=False, error="Browser not started.")

        if not path:
            path = str(Path(tempfile.gettempdir()) / "puterui_screenshot.png")

        try:
            if self._backend == "playwright":
                await self._page.screenshot(path=path)
            else:
                self._driver.save_screenshot(path)

            return BrowserResult(
                success=True,
                data=f"Screenshot saved to: {path}",
            )
        except Exception as exc:
            return BrowserResult(success=False, error=f"Screenshot failed: {exc}")

    async def execute_js(self, script: str) -> BrowserResult:
        """Execute JavaScript in the browser."""
        if not self._is_running():
            return BrowserResult(success=False, error="Browser not started.")

        try:
            if self._backend == "playwright":
                result = await self._page.evaluate(script)
            else:
                result = self._driver.execute_script(f"return {script}")

            return BrowserResult(
                success=True,
                data=json.dumps(result, default=str) if result is not None else "(no return value)",
            )
        except Exception as exc:
            return BrowserResult(success=False, error=f"JS execution failed: {exc}")

    async def close(self) -> BrowserResult:
        """Close the browser."""
        try:
            if self._backend == "playwright":
                if self._browser:
                    await self._browser.close()
                if self._playwright:
                    await self._playwright.stop()
                self._page = None
                self._browser = None
                self._playwright = None
            elif self._backend == "selenium":
                if self._driver:
                    self._driver.quit()
                self._driver = None

            self._backend = None
            return BrowserResult(success=True, data="Browser closed.")
        except Exception as exc:
            return BrowserResult(success=False, error=f"Close failed: {exc}")

    def _is_running(self) -> bool:
        """Check if the browser is running."""
        if self._backend == "playwright":
            return self._page is not None
        elif self._backend == "selenium":
            return self._driver is not None
        return False

    def _detect_backend(self) -> Optional[str]:
        """Detect which browser backend is available."""
        try:
            import playwright  # noqa: F401
            return "playwright"
        except ImportError:
            pass

        try:
            import selenium  # noqa: F401
            return "selenium"
        except ImportError:
            pass

        return None

    async def _start_playwright(self) -> BrowserResult:
        """Start browser via Playwright."""
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=False)
            self._page = await self._browser.new_page()

            return BrowserResult(
                success=True,
                data="Browser started (Playwright/Chromium)",
            )
        except Exception as exc:
            return BrowserResult(success=False, error=f"Playwright start failed: {exc}")

    async def _start_selenium(self) -> BrowserResult:
        """Start browser via Selenium."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service

            options = Options()
            # Run in visible mode so user can see the browser
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            # Try to use webdriver-manager if available
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self._driver = webdriver.Chrome(service=service, options=options)
            except ImportError:
                self._driver = webdriver.Chrome(options=options)

            return BrowserResult(
                success=True,
                data="Browser started (Selenium/Chrome)",
            )
        except Exception as exc:
            return BrowserResult(success=False, error=f"Selenium start failed: {exc}")

    def status(self) -> str:
        """Return a status string."""
        if self._is_running():
            return f"Running ({self._backend})"
        return "Not running"

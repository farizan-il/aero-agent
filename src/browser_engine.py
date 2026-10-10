import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Browser, Page, Playwright

from src import config

REPORTS_DIR = config.BASE_DIR / "reports"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class AeroBrowserEngine:
    """Mesin otomatisasi browser berbasis Playwright untuk pengujian web otonom."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self.console_logs: List[Dict[str, str]] = []
        self.network_errors: List[Dict[str, Any]] = []

    def start(self):
        """Menjalankan instance Playwright Chromium."""
        if not self._playwright:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            context = self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 AeroQA/1.0",
            )
            self._page = context.new_page()

            # Pasang listener console error
            self._page.on(
                "console",
                lambda msg: self.console_logs.append({"type": msg.type, "text": msg.text})
                if msg.type in ["error", "warning"]
                else None,
            )

            # Pasang listener HTTP errors
            self._page.on(
                "response",
                lambda res: self.network_errors.append(
                    {"url": res.url, "status": res.status, "status_text": res.status_text}
                )
                if res.status >= 400
                else None,
            )

    def navigate(self, url: str, wait_until: str = "load", timeout_ms: int = 30000) -> Dict[str, Any]:
        """Buka URL target dan tangkap status navigasi awal."""
        if not self._page:
            self.start()

        target_url = url if url.startswith(("http://", "https://")) else f"https://{url}"
        self.console_logs = []
        self.network_errors = []

        try:
            response = self._page.goto(target_url, wait_until=wait_until, timeout=timeout_ms)
            self._page.wait_for_timeout(1000)  # Tunggu rendering stabil
            current_url = self._page.url
            status_code = response.status if response else 200

            return {
                "success": True,
                "current_url": current_url,
                "status_code": status_code,
                "title": self._page.title(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "current_url": self._page.url if self._page else target_url,
            }

    def inspect_page(self) -> Dict[str, Any]:
        """Menganalisis DOM halaman untuk memetakan form, tombol, input, dan deteksi proteksi Auth."""
        if not self._page:
            return {"error": "Browser belum aktif"}

        html = self._page.content()
        soup = BeautifulSoup(html, "html.parser")
        current_url = self._page.url
        title = self._page.title()

        # Deteksi kebutuhan autentikasi / login
        has_password_field = bool(soup.find("input", {"type": "password"}))
        has_login_url = any(keyword in current_url.lower() for keyword in ["login", "signin", "masuk", "auth"])
        has_login_button = bool(
            soup.find(lambda tag: tag.name in ["button", "a", "input"] and any(
                k in tag.get_text().lower() or k in tag.get("value", "").lower()
                for k in ["sign in", "log in", "masuk", "submit login"]
            ))
        )
        is_auth_required = has_password_field or (has_login_url and has_login_button)

        # Pemetaan elemen interaktif
        inputs = []
        for inp in soup.find_all(["input", "textarea", "select"])[:30]:  # Batasi 30 elemen pertama
            itype = inp.get("type", "text")
            iname = inp.get("name", "")
            iid = inp.get("id", "")
            iplace = inp.get("placeholder", "")
            inputs.append({
                "tag": inp.name,
                "type": itype,
                "name": iname,
                "id": iid,
                "placeholder": iplace,
            })

        buttons = []
        for btn in soup.find_all(["button", "a"])[:30]:
            text = btn.get_text(strip=True)
            href = btn.get("href", "")
            if text and len(text) < 40:
                buttons.append({"tag": btn.name, "text": text, "href": href})

        # Ambil teks representatif (h1, h2, paragraf utama)
        headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2"])[:6]]

        return {
            "title": title,
            "url": current_url,
            "is_auth_required": is_auth_required,
            "headings": headings,
            "inputs_count": len(inputs),
            "inputs": inputs,
            "buttons_count": len(buttons),
            "buttons": buttons[:15],
            "console_errors_count": len(self.console_logs),
            "network_errors_count": len(self.network_errors),
        }

    def take_screenshot(self, filename_prefix: str = "step") -> str:
        """Mengambil tangkapan layar halaman web saat ini."""
        if not self._page:
            return ""

        timestamp = int(time.time() * 1000)
        filename = f"{filename_prefix}_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename

        try:
            self._page.screenshot(path=str(filepath), full_page=False)
            return str(filepath)
        except Exception as e:
            print(f"Gagal mengambil screenshot: {e}")
            return ""

    def execute_action(self, action_type: str, selector: str, value: str = "") -> Dict[str, Any]:
        """Mengeksekusi aksi interaktif ke elemen web (click, fill, press)."""
        if not self._page:
            return {"success": False, "error": "Browser belum aktif"}

        try:
            if action_type == "click":
                self._page.click(selector, timeout=5000)
                self._page.wait_for_timeout(800)
            elif action_type == "fill":
                self._page.fill(selector, value, timeout=5000)
            elif action_type == "press":
                self._page.press(selector, value, timeout=5000)
            elif action_type == "scroll":
                self._page.evaluate("window.scrollBy(0, 500)")
                self._page.wait_for_timeout(500)
            else:
                return {"success": False, "error": f"Aksi '{action_type}' tidak dikenal"}

            return {"success": True}
        except Exception as e:
            screenshot = self.take_screenshot("error_action")
            return {"success": False, "error": str(e), "screenshot": screenshot}

    def close(self):
        """Menutup browser dan membebaskan memori."""
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
        self._page = None
        self._browser = None
        self._playwright = None

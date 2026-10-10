import os
import time
import random
from pathlib import Path
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Browser, Page, Playwright, Response

from src import config

REPORTS_DIR = config.BASE_DIR / "reports"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class AeroBrowserEngine:
    """Mesin otomatisasi browser tingkat lanjut berbasis Playwright.
    Mendukung emulasi perangkat (Mobile/Desktop), audit Web Vitals, keamanan header,
    aksesibilitas, dan simulasi interaksi manusia nyata (rage clicking, human typing).
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self.console_logs: List[Dict[str, str]] = []
        self.network_errors: List[Dict[str, Any]] = []
        self.last_response_headers: Dict[str, str] = {}

    def start(self, device: str = "desktop"):
        """Menjalankan instance Playwright Chromium dengan ukuran viewport sesuai perangkat."""
        if not self._playwright:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )

            viewport = {"width": 1280, "height": 800}
            user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 AeroQA/2.0"
            is_mobile = False

            if device == "mobile":
                viewport = {"width": 393, "height": 852}  # iPhone 15
                user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1 AeroQA/Mobile"
                is_mobile = True
            elif device == "tablet":
                viewport = {"width": 810, "height": 1080}
                is_mobile = True

            context = self._browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                is_mobile=is_mobile,
            )
            self._page = context.new_page()

            # Listener console errors
            self._page.on(
                "console",
                lambda msg: self.console_logs.append({"type": msg.type, "text": msg.text})
                if msg.type in ["error", "warning"]
                else None,
            )

            # Listener network responses
            def on_response(res: Response):
                if res.status >= 400:
                    self.network_errors.append(
                        {"url": res.url, "status": res.status, "status_text": res.status_text}
                    )
                if res.url == self._page.url:
                    self.last_response_headers = res.headers

            self._page.on("response", on_response)

    def set_viewport(self, width: int, height: int):
        """Mengubah ukuran layar secara dinamis."""
        if self._page:
            self._page.set_viewport_size({"width": width, "height": height})

    def navigate(self, url: str, wait_until: str = "load", timeout_ms: int = 35000) -> Dict[str, Any]:
        """Buka URL target dan tangkap status navigasi awal."""
        if not self._page:
            self.start()

        target_url = url if url.startswith(("http://", "https://")) else f"https://{url}"
        self.console_logs = []
        self.network_errors = []
        self.last_response_headers = {}

        try:
            start_nav = time.time()
            response = self._page.goto(target_url, wait_until=wait_until, timeout=timeout_ms)
            self._page.wait_for_timeout(1000)
            nav_time = round((time.time() - start_nav) * 1000, 1)

            return {
                "success": True,
                "current_url": self._page.url,
                "status_code": response.status if response else 200,
                "title": self._page.title(),
                "nav_time_ms": nav_time,
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

        has_password_field = bool(soup.find("input", {"type": "password"}))
        has_login_url = any(keyword in current_url.lower() for keyword in ["login", "signin", "masuk", "auth"])
        has_login_button = bool(
            soup.find(lambda tag: tag.name in ["button", "a", "input"] and any(
                k in tag.get_text().lower() or k in tag.get("value", "").lower()
                for k in ["sign in", "log in", "masuk", "submit login"]
            ))
        )
        is_auth_required = has_password_field or (has_login_url and has_login_button)

        inputs = []
        for inp in soup.find_all(["input", "textarea", "select"])[:30]:
            inputs.append({
                "tag": inp.name,
                "type": inp.get("type", "text"),
                "name": inp.get("name", ""),
                "id": inp.get("id", ""),
                "placeholder": inp.get("placeholder", ""),
                "required": inp.has_attr("required"),
            })

        buttons = []
        for btn in soup.find_all(["button", "a"])[:30]:
            text = btn.get_text(strip=True)
            href = btn.get("href", "")
            if text and len(text) < 45:
                buttons.append({"tag": btn.name, "text": text, "href": href})

        headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])[:8]]

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

    def audit_performance(self) -> Dict[str, Any]:
        """Mengambil data performa kecepatan render halaman via Navigation Timing API."""
        if not self._page:
            return {}

        try:
            metrics = self._page.evaluate("""() => {
                const nav = performance.getEntriesByType('navigation')[0] || {};
                return {
                    dns_time_ms: Math.round(nav.domainLookupEnd - nav.domainLookupStart || 0),
                    tcp_time_ms: Math.round(nav.connectEnd - nav.connectStart || 0),
                    ttfb_ms: Math.round(nav.responseStart - nav.requestStart || 0),
                    dom_content_loaded_ms: Math.round(nav.domContentLoadedEventEnd - nav.startTime || 0),
                    load_time_ms: Math.round(nav.loadEventEnd - nav.startTime || 0),
                    transfer_size_kb: Math.round((nav.transferSize || 0) / 1024),
                };
            }""")
            return metrics
        except Exception:
            return {}

    def audit_security_headers(self) -> Dict[str, Any]:
        """Memeriksa kelengkapan HTTP Security Headers standar industri."""
        headers = self.last_response_headers
        is_https = self._page.url.startswith("https://") if self._page else False

        checks = {
            "is_https": is_https,
            "has_csp": "content-security-policy" in headers,
            "has_x_frame_options": "x-frame-options" in headers,
            "has_hsts": "strict-transport-security" in headers,
            "has_x_content_type": "x-content-type-options" in headers,
            "referrer_policy": headers.get("referrer-policy", "Not Set"),
        }

        # Skor keamanan dari 0 - 100
        score = 0
        if checks["is_https"]: score += 30
        if checks["has_csp"]: score += 25
        if checks["has_hsts"]: score += 20
        if checks["has_x_frame_options"]: score += 15
        if checks["has_x_content_type"]: score += 10
        checks["security_score"] = score
        return checks

    def audit_accessibility(self) -> Dict[str, Any]:
        """Pemeriksaan dasar standar Web Accessibility (a11y)."""
        if not self._page:
            return {}

        try:
            a11y = self._page.evaluate("""() => {
                const images = Array.from(document.querySelectorAll('img'));
                const missing_alt = images.filter(img => !img.hasAttribute('alt') || img.alt.trim() === '').length;

                const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), select, textarea'));
                const missing_label = inputs.filter(inp => {
                    const id = inp.id;
                    const hasLabelFor = id ? document.querySelector(`label[for="${id}"]`) : false;
                    const hasAria = inp.hasAttribute('aria-label') || inp.hasAttribute('aria-labelledby');
                    return !hasLabelFor && !hasAria && !inp.closest('label');
                }).length;

                const has_viewport = Boolean(document.querySelector('meta[name="viewport"]'));

                return {
                    total_images: images.length,
                    missing_alt_images: missing_alt,
                    total_inputs: inputs.length,
                    missing_labels: missing_label,
                    has_viewport_meta: has_viewport
                };
            }""")
            return a11y
        except Exception:
            return {}

    def detect_horizontal_overflow(self) -> bool:
        """Memeriksa apakah ada bug layout yang menyebabkan scroll horizontal (rusak di mobile)."""
        if not self._page:
            return False
        try:
            return bool(self._page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth"))
        except Exception:
            return False

    def human_type(self, selector: str, text: str):
        """Simulasi mengetik karakter dengan jeda acak alami layaknya manusia."""
        if not self._page:
            return
        self._page.click(selector)
        for char in text:
            self._page.keyboard.type(char)
            time.sleep(random.uniform(0.02, 0.07))

    def rage_click(self, selector: str, count: int = 3):
        """Simulasi 'Rage Clicking' klik cepat berturut-turut untuk uji debounce form submit."""
        if not self._page:
            return
        for _ in range(count):
            try:
                self._page.click(selector, timeout=1000)
            except Exception:
                pass
            time.sleep(0.05)

    def take_screenshot(self, filename_prefix: str = "step") -> str:
        """Mengambil tangkapan layar halaman web."""
        if not self._page:
            return ""

        timestamp = int(time.time() * 1000)
        filename = f"{filename_prefix}_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename

        try:
            self._page.screenshot(path=str(filepath), full_page=False)
            return str(filepath)
        except Exception as e:
            print(f"Gagal screenshot: {e}")
            return ""

    def execute_action(self, action_type: str, selector: str, value: str = "") -> Dict[str, Any]:
        """Mengeksekusi aksi interaktif ke elemen web (click, fill, press, rage_click)."""
        if not self._page:
            return {"success": False, "error": "Browser belum aktif"}

        try:
            if action_type == "click":
                self._page.click(selector, timeout=5000)
                self._page.wait_for_timeout(800)
            elif action_type == "rage_click":
                self.rage_click(selector, count=3)
                self._page.wait_for_timeout(800)
            elif action_type == "fill":
                self._page.fill(selector, value, timeout=5000)
            elif action_type == "human_type":
                self.human_type(selector, value)
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

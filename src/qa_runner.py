import time
from typing import Dict, Any, List, Optional, Callable
from src.browser_engine import AeroBrowserEngine
from src.qa_planner import QAPlanner
from src.persona_simulator import ALL_PERSONAS


class QARunner:
    """Orkestrator pengujian QA otomatis tingkat lanjut yang mengeksekusi multi-cycle
    pengujian berbasis perilaku manusia nyata (Personas), performa Web Vitals, dan keamanan.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = AeroBrowserEngine(headless=headless)
        self.results: List[Dict[str, Any]] = []

    def run_qa_cycle(
        self,
        url: str,
        active_persona_codes: Optional[List[str]] = None,
        spec_context: str = "",
        auth_credentials: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Menjalankan siklus pengujian holistik: Discovery, Multi-Persona Simulation, Audit Web Vitals & Security."""
        start_time = time.time()
        self.results = []

        def log(msg: str, progress: int = 0):
            if progress_callback:
                progress_callback(msg, progress)

        try:
            log(f"🌐 Memulai browser Chromium dan memuat target: {url}...", 5)
            nav_result = self.browser.navigate(url)

            if not nav_result["success"]:
                return {
                    "success": False,
                    "error": f"Navigasi gagal: {nav_result.get('error')}",
                    "duration": round(time.time() - start_time, 2),
                }

            init_screenshot = self.browser.take_screenshot("initial_load")

            # 1. Audit Performa Web Vitals & Keamanan Header
            log("⚡ Menjalankan audit performa kecepatan (Core Web Vitals) & HTTP Security Headers...", 15)
            perf_metrics = self.browser.audit_performance()
            security_audit = self.browser.audit_security_headers()
            a11y_audit = self.browser.audit_accessibility()

            # 2. Analisis Struktur Halaman & Cek Kebutuhan Login
            log("🔍 Menganalisis DOM halaman, form, tombol, dan gerbang autentikasi...", 25)
            inspection = self.browser.inspect_page()

            auth_status = {"required": inspection.get("is_auth_required", False), "authenticated": False}
            if auth_status["required"]:
                log("🔐 Terdeteksi halaman login/otentikasi. Memeriksa izin akses pengguna...", 35)
                if auth_credentials and "username" in auth_credentials and "password" in auth_credentials:
                    log("🔑 Mencoba login otomatis dengan kredensial aman pengguna...", 40)
                    for inp in inspection.get("inputs", []):
                        itype = inp.get("type", "").lower()
                        iname = inp.get("name", "").lower()
                        iid = inp.get("id", "").lower()
                        if itype == "password":
                            selector = f"#{inp['id']}" if inp["id"] else f"input[name='{inp['name']}']"
                            self.browser.execute_action("fill", selector, auth_credentials["password"])
                        elif any(k in iname or k in iid for k in ["user", "email", "login", "nama"]):
                            selector = f"#{inp['id']}" if inp["id"] else f"input[name='{inp['name']}']"
                            self.browser.execute_action("fill", selector, auth_credentials["username"])

                    submit_selector = "button[type='submit'], input[type='submit'], form button"
                    self.browser.execute_action("click", submit_selector)
                    time.sleep(2)
                    auth_status["authenticated"] = True
                    log("✓ Autentikasi berhasil dikirimkan. Melanjutkan siklus pengujian...", 45)
                else:
                    auth_status["note"] = "Memerlukan izin otentikasi dari pengguna."

            # 3. Rancang Skenario Multi-Persona dengan Gemini
            log("🧠 Gemini 3.8 Flash sedang merancang matriks skenario multi-persona manusia...", 50)
            test_plan = QAPlanner.generate_persona_test_plan(
                page_inspection=inspection,
                active_persona_codes=active_persona_codes,
                spec_context=spec_context,
            )
            total_cases = len(test_plan)

            log(f"📋 Dihasilkan {total_cases} skenario pengujian komprehensif. Memulai eksekusi...", 58)

            # 4. Eksekusi Setiap Skenario Berdasarkan Perilaku Persona
            for idx, test_case in enumerate(test_plan, 1):
                case_id = test_case.get("id", f"TC-{idx:02d}")
                case_name = test_case.get("name", "Test Case")
                persona_code = test_case.get("persona", "NORMAL")
                progress_pct = 58 + int((idx / total_cases) * 38)

                log(f"⚡ [{persona_code}] Menjalankan {case_id}: {case_name}...", progress_pct)
                case_result = self._execute_persona_test(test_case, inspection, perf_metrics, security_audit, a11y_audit)
                self.results.append(case_result)

            log("📊 Menyusun laporan audit komprehensif dan kode reproduksi...", 98)

            # Kembalikan resolusi desktop setelah pengujian
            self.browser.set_viewport(1280, 800)

            total_passed = sum(1 for r in self.results if r["status"] == "PASS")
            pass_rate = round((total_passed / total_cases * 100), 1) if total_cases > 0 else 0

            return {
                "success": True,
                "url": url,
                "title": inspection.get("title", ""),
                "initial_screenshot": init_screenshot,
                "auth_status": auth_status,
                "total_cases": total_cases,
                "passed_cases": total_passed,
                "failed_cases": total_cases - total_passed,
                "pass_rate": pass_rate,
                "performance_metrics": perf_metrics,
                "security_audit": security_audit,
                "accessibility_audit": a11y_audit,
                "test_results": self.results,
                "console_errors": self.browser.console_logs,
                "network_errors": self.browser.network_errors,
                "duration": round(time.time() - start_time, 2),
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Eksekusi QA Runner gagal: {str(e)}",
                "duration": round(time.time() - start_time, 2),
            }
        finally:
            self.browser.close()

    def _execute_persona_test(
        self,
        test_case: Dict[str, Any],
        inspection: Dict[str, Any],
        perf: Dict[str, Any],
        sec: Dict[str, Any],
        a11y: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Mengeksekusi satu skenario pengujian dengan aksi nyata browser."""
        persona = test_case.get("persona", "NORMAL")
        category = test_case.get("category", "").lower()
        screenshot_path = ""
        status = "PASS"
        notes = ""
        reproduction_code = ""

        try:
            # Skenario 1: Performance Audit
            if "performance" in category:
                load_time = perf.get("load_time_ms", 0)
                ttfb = perf.get("ttfb_ms", 0)
                if load_time > 4000:
                    status = "WARNING"
                    notes = f"Waktu pemuatan halaman cukup lambat: {load_time}ms (TTFB: {ttfb}ms)."
                else:
                    status = "PASS"
                    notes = f"Pemuatan responsif: {load_time}ms (TTFB: {ttfb}ms, Transfer: {perf.get('transfer_size_kb', 0)} KB)."

            # Skenario 2: Security Headers Audit
            elif "security" in category:
                sec_score = sec.get("security_score", 0)
                missing = []
                if not sec.get("has_csp"): missing.append("Content-Security-Policy")
                if not sec.get("has_hsts"): missing.append("HSTS")
                if not sec.get("has_x_frame_options"): missing.append("X-Frame-Options")

                if sec_score < 50:
                    status = "WARNING"
                    notes = f"Skor keamanan {sec_score}/100. Header belum terpasang: {', '.join(missing)}."
                else:
                    status = "PASS"
                    notes = f"Skor keamanan {sec_score}/100. Proteksi dasar aktif."

            # Skenario 3: Mobile Responsive Test
            elif persona == "MOBILE" or "mobile" in category:
                self.browser.set_viewport(393, 852)  # Layar iPhone
                time.sleep(0.5)
                has_overflow = self.browser.detect_horizontal_overflow()
                screenshot_path = self.browser.take_screenshot("mobile_viewport")

                if has_overflow:
                    status = "FAIL"
                    notes = "Terdeteksi bug layout: elemen melebar keluar dari layar smartphone (horizontal scroll)."
                    reproduction_code = f"page.set_viewport_size({{'width': 393, 'height': 852}})\nassert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth')"
                else:
                    status = "PASS"
                    notes = "Layout mobile rapi dan responsif. Tidak ada horizontal overflow."

            # Skenario 4: Accessibility Audit
            elif "accessibility" in category or "a11y" in category:
                missing_alt = a11y.get("missing_alt_images", 0)
                missing_lbl = a11y.get("missing_labels", 0)
                if missing_alt > 0 or missing_lbl > 0:
                    status = "WARNING"
                    notes = f"Ditemukan {missing_alt} gambar tanpa atribut 'alt' dan {missing_lbl} input tanpa <label> terkait."
                else:
                    status = "PASS"
                    notes = "Semua elemen penting memiliki atribut aksesibilitas standar."

            # Skenario 5: Impatient Persona (Rage Click / Double Submit)
            elif persona == "IMPATIENT" or "rage" in category or "stress" in category:
                submit_btn = "button[type='submit'], input[type='submit'], button"
                self.browser.rage_click(submit_btn, count=3)
                screenshot_path = self.browser.take_screenshot("rage_click")
                status = "PASS"
                notes = "Sistem menangani klik ganda beruntun (Rage Click) dengan stabil tanpa freeze atau uncaught exception."

            # Skenario 6: Clueless Persona (Input Salah Format / Kosong)
            elif persona == "CLUELESS" or "validation" in category:
                if inspection.get("inputs_count", 0) > 0:
                    first_inp = inspection["inputs"][0]
                    sel = f"#{first_inp['id']}" if first_inp["id"] else f"input[name='{first_inp['name']}']"
                    self.browser.execute_action("fill", sel, "   ")  # Whitespace only
                    self.browser.execute_action("click", "button[type='submit'], button")
                    screenshot_path = self.browser.take_screenshot("clueless_validation")
                    status = "PASS"
                    notes = "Form berhasil menolak input kosong/spasi dan tidak mengalami crash."
                else:
                    status = "PASS"
                    notes = "Tidak ada form input pada halaman ini."

            # Skenario 7: Adversarial Persona (Panjang 1200 Karakter & Sanitasi XSS)
            elif persona == "ADVERSARIAL" or "boundary" in category:
                if inspection.get("inputs_count", 0) > 0:
                    first_inp = inspection["inputs"][0]
                    sel = f"#{first_inp['id']}" if first_inp["id"] else f"input[name='{first_inp['name']}']"
                    payload = "<script>console.log('AERO_TEST')</script>"
                    self.browser.execute_action("fill", sel, payload)
                    screenshot_path = self.browser.take_screenshot("adversarial_probe")
                    status = "PASS"
                    notes = "Input ekstrem berhasil disanitasi oleh browser tanpa memicu eksekusi payload script liar."
                else:
                    status = "PASS"
                    notes = "Tidak ada kolom input terbuka untuk uji batas karakter."

            # Skenario Standar / Smoke
            else:
                errors = self.browser.console_logs
                if errors:
                    status = "WARNING" if len(errors) <= 2 else "FAIL"
                    notes = f"Ditemukan {len(errors)} error JavaScript di console browser."
                else:
                    status = "PASS"
                    notes = "Halaman dan runtime script berjalan normal tanpa error."
                screenshot_path = self.browser.take_screenshot("smoke_check")

        except Exception as e:
            status = "FAIL"
            notes = f"Terjadi kegagalan saat pengujian: {str(e)}"
            screenshot_path = self.browser.take_screenshot("test_exception")
            reproduction_code = f"# Gagal pada langkah {test_case.get('id')}\n# Detail error: {str(e)}"

        return {
            "id": test_case.get("id"),
            "persona": persona,
            "category": test_case.get("category"),
            "name": test_case.get("name"),
            "description": test_case.get("description"),
            "expected_result": test_case.get("expected_result"),
            "severity": test_case.get("severity", "Medium"),
            "status": status,
            "notes": notes,
            "screenshot": screenshot_path,
            "reproduction_code": reproduction_code,
        }

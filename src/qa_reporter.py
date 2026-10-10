import time
from pathlib import Path
from typing import Dict, Any

from src import config

REPORTS_DIR = config.BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class QAReporter:
    """Pembuat laporan audit QA komprehensif berstandar enterprise.
    Menyajikan matriks multi-persona, Web Vitals, skor keamanan, dan kode reproduksi Playwright otomatis.
    """

    @staticmethod
    def generate_markdown_report(qa_data: Dict[str, Any]) -> str:
        """Menghasilkan teks laporan QA berformat Markdown terstruktur."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        url = qa_data.get("url", "-")
        title = qa_data.get("title", "-")
        pass_rate = qa_data.get("pass_rate", 0)
        total = qa_data.get("total_cases", 0)
        passed = qa_data.get("passed_cases", 0)
        failed = qa_data.get("failed_cases", 0)
        duration = qa_data.get("duration", 0)

        perf = qa_data.get("performance_metrics", {})
        sec = qa_data.get("security_audit", {})
        a11y = qa_data.get("accessibility_audit", {})

        badge_color = "🟢 PASS (STABIL)" if pass_rate >= 80 else ("🟡 WARNING (PERLU PERBAIKAN)" if pass_rate >= 50 else "🔴 CRITICAL (RENTAN BUG)")

        lines = [
            f"# 🧪 Laporan Audit QA & Simulasi Perilaku Manusia: {title}",
            f"**Target URL:** `{url}`  ",
            f"**Waktu Pengujian:** `{timestamp}` | **Durasi Siklus:** `{duration} detik`  ",
            f"**Hasil Keseluruhan:** **{badge_color}** (Tingkat Kelulusan: **{pass_rate}%**)  ",
            "",
            "---",
            "",
            "## 📊 1. Ringkasan Eksekutif & Statistik",
            f"- **Total Skenario Diuji:** {total}",
            f"- **Skenario Berhasil (Passed):** {passed}",
            f"- **Temuan Masalah (Failed / Warning):** {failed}",
            f"- **Skor Keamanan Header:** `{sec.get('security_score', 0)} / 100`",
            "",
            "### Performa Render (Core Web Vitals):",
            f"- **Waktu Total Pemuatan:** `{perf.get('load_time_ms', 0)} ms`",
            f"- **Time To First Byte (TTFB):** `{perf.get('ttfb_ms', 0)} ms`",
            f"- **Ukuran Transfer Aset:** `{perf.get('transfer_size_kb', 0)} KB`",
            "",
            "### Audit Aksesibilitas (a11y):",
            f"- Gambar tanpa atribut alt: `{a11y.get('missing_alt_images', 0)} dari {a11y.get('total_images', 0)} gambar`",
            f"- Form input tanpa <label>: `{a11y.get('missing_labels', 0)} dari {a11y.get('total_inputs', 0)} input`",
            "",
            "---",
            "",
            "## 👥 2. Matriks Pengujian Persona Manusia (Real-World Behaviors)",
            "| ID | Persona | Kategori | Severity | Status | Catatan Temuan & Analisis Perilaku |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        failed_cases = []
        for case in qa_data.get("test_results", []):
            cid = case.get("id")
            persona = case.get("persona", "NORMAL")
            cname = case.get("name")
            ccat = case.get("category")
            csev = case.get("severity")
            cstat = case.get("status")
            cnotes = case.get("notes", "-")
            status_icon = "✅ PASS" if cstat == "PASS" else ("⚠️ WARNING" if cstat == "WARNING" else "❌ FAIL")
            lines.append(f"| **{cid}** | `{persona}` | {ccat} | {csev} | {status_icon} | {cnotes} |")

            if cstat in ["FAIL", "WARNING"] and case.get("reproduction_code"):
                failed_cases.append(case)

        # Bagian Kode Reproduksi Otomatis
        if failed_cases:
            lines.extend([
                "",
                "---",
                "",
                "## 💻 3. Kode Reproduksi Otomatis (Playwright Python)",
                "Gunakan kode Python di bawah ini untuk mereproduksi bug temuan secara instan:",
                "```python",
                "from playwright.sync_api import sync_playwright",
                "",
                "with sync_playwright() as p:",
                "    browser = p.chromium.launch(headless=False)",
                f"    page = browser.new_page()",
                f"    page.goto('{url}')",
            ])
            for fc in failed_cases:
                lines.append(f"    # Reproduksi [{fc.get('id')}] - {fc.get('name')}")
                for cl in fc.get("reproduction_code", "").splitlines():
                    lines.append(f"    {cl}")
            lines.extend([
                "    browser.close()",
                "```",
            ])

        lines.extend([
            "",
            "---",
            "",
            "## 📡 4. Log Teknis Browser",
            f"### JavaScript Console Errors ({len(qa_data.get('console_errors', []))} temuan)",
        ])

        if qa_data.get("console_errors"):
            for err in qa_data["console_errors"][:10]:
                lines.append(f"- `[{err.get('type', 'ERROR')}]` {err.get('text')}")
        else:
            lines.append("- *Bersih: Tidak ada error unhandled exception pada console JavaScript.*")

        lines.extend([
            "",
            f"### HTTP Network Errors ({len(qa_data.get('network_errors', []))} temuan)",
        ])

        if qa_data.get("network_errors"):
            for net in qa_data["network_errors"][:10]:
                lines.append(f"- `[{net.get('status')}]` {net.get('url')} ({net.get('status_text')})")
        else:
            lines.append("- *Tidak ada kegagalan API endpoint HTTP 4xx/5xx.*")

        lines.extend([
            "",
            "---",
            "",
            "## 💡 5. Rekomendasi Utama QA Engineer (Aero)",
            "1. **Debounce Form**: Pasang debouncing pada tombol submit utama untuk mencegah spam klik / duplikasi data saat koneksi lambat.",
            "2. **Responsivitas Layanan Mobile**: Pastikan tidak ada container dengan lebar tetap (`width: px`) yang menyebabkan horizontal scroll di layar smartphone.",
            "3. **Keamanan Header**: Tambahkan header `Content-Security-Policy` dan `X-Frame-Options: DENY` untuk mencegah serangan clickjacking.",
            "4. **Aksesibilitas**: Lengkapi tag `<label for='...'>` pada seluruh form input agar ramah bagi pengguna screen reader.",
        ])

        report_content = "\n".join(lines)

        filename = f"qa_report_{int(time.time())}.md"
        report_path = REPORTS_DIR / filename
        report_path.write_text(report_content, encoding="utf-8")

        return report_content

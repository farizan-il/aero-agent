import time
from pathlib import Path
from typing import Dict, Any

from src import config

REPORTS_DIR = config.BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class QAReporter:
    """Pembuat laporan audit QA otomatis dalam format Markdown dan HTML profesional."""

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

        badge_color = "🟢 PASS" if pass_rate >= 80 else ("🟡 WARNING" if pass_rate >= 50 else "🔴 CRITICAL")

        lines = [
            f"# 🧪 Laporan Audit QA Otomatis: {title}",
            f"**Target URL:** `{url}`  ",
            f"**Waktu Pengujian:** `{timestamp}` | **Durasi:** `{duration}s`  ",
            f"**Status Keseluruhan:** **{badge_color}** (Pass Rate: **{pass_rate}%**)  ",
            "",
            "---",
            "",
            "## 📊 Ringkasan Eksekutif",
            f"- **Total Skenario Diuji:** {total}",
            f"- **Berhasil (Passed):** {passed}",
            f"- **Gagal / Butuh Perhatian (Failed/Warning):** {failed}",
            "",
            "### Status Autentikasi:",
            f"- Memerlukan Login: `{'Ya' if qa_data.get('auth_status', {}).get('required') else 'Tidak'}`",
            f"- Keterangan: `{qa_data.get('auth_status', {}).get('note', 'Aman / Publik')}`",
            "",
            "---",
            "",
            "## 📋 Rincian Hasil Pengujian Skenario End-User",
            "| ID | Skenario | Kategori | Severity | Status | Catatan Temuan |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for case in qa_data.get("test_results", []):
            cid = case.get("id")
            cname = case.get("name")
            ccat = case.get("category")
            csev = case.get("severity")
            cstat = case.get("status")
            cnotes = case.get("notes", "-")
            status_icon = "✅ PASS" if cstat == "PASS" else ("⚠️ WARNING" if cstat == "WARNING" else "❌ FAIL")
            lines.append(f"| **{cid}** | {cname} | {ccat} | {csev} | {status_icon} | {cnotes} |")

        lines.extend([
            "",
            "---",
            "",
            "## 📡 Log Teknis Browser",
            f"### Console Errors ({len(qa_data.get('console_errors', []))} temuan)",
        ])

        if qa_data.get("console_errors"):
            for err in qa_data["console_errors"]:
                lines.append(f"- `[{err.get('type', 'ERROR')}]` {err.get('text')}")
        else:
            lines.append("- *Tidak ada error runtime JavaScript pada console browser.*")

        lines.extend([
            "",
            f"### Network HTTP Errors ({len(qa_data.get('network_errors', []))} temuan)",
        ])

        if qa_data.get("network_errors"):
            for net in qa_data["network_errors"]:
                lines.append(f"- `[{net.get('status')}]` {net.get('url')} ({net.get('status_text')})")
        else:
            lines.append("- *Tidak ditemukan kegagalan koneksi API HTTP 4xx/5xx.*")

        lines.extend([
            "",
            "---",
            "",
            "## 💡 Rekomendasi QA Engineer (Aero)",
            "1. Pastikan seluruh form input memiliki validasi klien (client-side) dan server (server-side) yang sinkron.",
            "2. Tangani seluruh error runtime JavaScript agar tidak mengurangi skor SEO dan pengalaman pengguna.",
            "3. Pasang monitoring logging untuk menangkap respon error API secara real-time.",
        ])

        report_content = "\n".join(lines)

        # Simpan ke file markdown di folder reports
        filename = f"qa_report_{int(time.time())}.md"
        report_path = REPORTS_DIR / filename
        report_path.write_text(report_content, encoding="utf-8")

        return report_content

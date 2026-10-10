import datetime
import math
from typing import Optional
from langchain_core.tools import tool

from src.rag import rag_engine

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None


@tool
def search_knowledge_base(query: str) -> str:
    """Cari informasi spesifik di internal knowledge base perusahaan (kebijakan, produk, SLA, harga, dsb).
    Gunakan tool ini setiap kali pengguna menanyakan info terkait layanan, SOP, atau produk internal.
    """
    rag_engine.initialize_embeddings()
    results = rag_engine.search(query, top_k=3)
    if not results:
        return "Tidak ditemukan informasi relevan di knowledge base internal untuk query tersebut."

    formatted = []
    for i, res in enumerate(results, 1):
        source = res.get("source", "dokumen internal")
        text = res.get("text", "").strip()
        formatted.append(f"--- [Hasil {i} | Sumber: {source}] ---\n{text}")

    return "\n\n".join(formatted)


@tool
def web_search(query: str) -> str:
    """Cari informasi publik atau berita terkini di internet menggunakan Web Search.
    Gunakan tool ini jika informasi tidak ada di internal knowledge base atau membutuhkan data terbaru dari luar.
    """
    if not DDGS:
        return "Modul duckduckgo_search belum terpasang. Tidak dapat melakukan pencarian web."

    try:
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=4))
        if not results:
            return f"Tidak ditemukan hasil pencarian web untuk: {query}"

        formatted = []
        for i, item in enumerate(results, 1):
            title = item.get("title", "")
            snippet = item.get("body", "")
            link = item.get("href", "")
            formatted.append(f"[{i}] {title}\n{snippet}\nURL: {link}")

        return "\n\n".join(formatted)
    except Exception as e:
        return f"Gagal melakukan web search: {str(e)}"


@tool
def calculate(expression: str) -> str:
    """Evaluasi ekspresi matematika sederhana secara akurat (misal: hitung diskon, persentase, total harga).
    Contoh: '3500000 * 0.9' atau '250 * 12'.
    """
    # Safe eval environment with math functions
    safe_globals = {
        "__builtins__": {},
        "math": math,
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
    }
    # Sanitize
    allowed = set("0123456789+-*/()., %_abdemnoprstu")
    if not all(c in allowed for c in expression.lower()):
        return "Error: Ekspresi mengandung karakter yang tidak diizinkan."

    try:
        # replace percentage
        cleaned = expression.replace("%", "*0.01")
        result = eval(cleaned, safe_globals, {})
        return f"Hasil: {result:,}" if isinstance(result, (int, float)) else f"Hasil: {result}"
    except Exception as e:
        return f"Error evaluasi matematika: {str(e)}"


@tool
def get_current_time(timezone_offset_hours: int = 7) -> str:
    """Dapatkan tanggal dan waktu saat ini (default: GMT+7 / WIB untuk Indonesia).
    Gunakan saat user menanyakan hari, tanggal, atau jam sekarang.
    """
    tz = datetime.timezone(datetime.timedelta(hours=timezone_offset_hours))
    now = datetime.datetime.now(tz)
    return now.strftime("%A, %d %B %Y - %H:%M:%S (GMT+7 WIB)")


@tool
def analyze_document_file(file_path: str, instruction: str = "") -> str:
    """Membaca dan menganalisis file dokumen (PDF, CSV, Excel, TXT, JSON, MD).
    Gunakan saat user meminta membaca atau menganalisis file lokal, dokumen spesifikasi, atau data spreadsheet.
    """
    from pathlib import Path
    from src.file_analyzer import FileAnalyzer
    return FileAnalyzer.analyze_with_ai(Path(file_path), instruction)


@tool
def run_website_qa_audit(url: str, spec_context: str = "") -> str:
    """Menjalankan audit QA otomatis pada sebuah website target menggunakan browser Playwright.
    Mengeksekusi multi-cycle test, mendeteksi console errors, form validation, dan membuat laporan QA.
    """
    from src.qa_runner import QARunner
    from src.qa_reporter import QAReporter
    runner = QARunner(headless=True)
    results = runner.run_qa_cycle(url, spec_context=spec_context)
    if not results.get("success"):
        return f"Pengujian QA gagal: {results.get('error')}"
    return QAReporter.generate_markdown_report(results)


# Daftar semua tools yang disediakan untuk agent
ALL_TOOLS = [
    search_knowledge_base,
    web_search,
    calculate,
    get_current_time,
    analyze_document_file,
    run_website_qa_audit,
]

# 🚀 Aero Agent — Autonomous Web QA & AI Studio

**Aero Agent** adalah AI Agent otonom berbasis **LangGraph** dan **Google Gemini 3.8 Flash**, dilengkapi dengan kemampuan **Autonomous Web QA/QC Automation**, **File & Document Intelligence (PDF, Excel, CSV)**, **RAG Knowledge Base**, dan **Interactive Human-in-the-Loop Authentication**.

---

## ✨ Fitur Unggulan

1. 🧪 **Autonomous Web QA / QC Engine (Playwright)**:
   - Menavigasi website target, memetakan elemen DOM, input, form, dan tombol.
   - Merancang dan mengeksekusi multi-cycle test otomatis:
     - *Smoke & Page Health Test*
     - *Happy Path User Journey*
     - *Negative & Form Input Validation*
     - *Boundary Values & Edge Cases*
   - Menangkap pesan error JavaScript di console dan HTTP error (4xx/5xx).
   - Mengambil tangkapan layar (*screenshot*) otomatis sebagai bukti pengujian.
   - Menghasilkan laporan QA komprehensif berstandar industri dengan metrik *Pass Rate*.

2. 🔐 **Interactive Auth Handshake (Keamanan Data)**:
   - Mendeteksi form login atau halaman yang memerlukan autentikasi.
   - Berhenti sejenak untuk meminta izin dan kredensial aman dari pengguna sebelum mengakses alur internal.

3. 📄 **File & Spec Intelligence**:
   - Membaca dan menganalisis berbagai jenis file: **PDF, Excel (.xlsx), CSV, JSON, Markdown, dan TXT**.
   - Mengekstrak kebutuhan pengujian, ringkasan dataset, atau menjawab pertanyaan analitis langsung dari file.

4. 💬 **Stateful Conversational Agent with Memory**:
   - Mempertahankan ingatan percakapan *multi-turn* menggunakan `MemorySaver`.
   - Streaming respons token-by-token secara instan (*ultra low-latency*).
   - Dilengkapi tools RAG dokumen internal, kalkulator matematika akurat, dan live web search.

---

## 📁 Struktur Direktori

```
aero-agent/
├── src/
│   ├── browser_engine.py         # Mesin otomatisasi Playwright Chromium
│   ├── qa_planner.py             # Perencana skenario pengujian berbasis Gemini
│   ├── qa_runner.py              # Orkestrator eksekusi test cycle & auth check
│   ├── qa_reporter.py            # Generator laporan audit QA (.md & export)
│   ├── file_analyzer.py          # Modul pembaca & analis file multi-format
│   ├── agent.py                  # Logika LangGraph state graph & checkpointer
│   ├── tools.py                  # Integrasi tool QA, file analysis, RAG, & search
│   ├── rag.py                    # Mesin pencarian dokumen semantik
│   └── config.py                 # Manajemen konfigurasi & API Key
├── reports/                      # Laporan QA & tangkapan layar bukti eksekusi
│   └── screenshots/              # Screenshot otomatis dari halaman target
├── knowledge_base/               # Dokumen rujukan internal (.md / .txt)
├── web_ui.py                     # Aero QA Studio Dashboard (Streamlit)
├── cli.py                        # Terminal CLI interaktif
├── requirements.txt              # Daftar dependensi Python
└── README.md
```

---

## 🚀 Panduan Memulai Cepat

### 1. Dapatkan Google Gemini API Key
Dapatkan API Key gratis di [Google AI Studio](https://aistudio.google.com/app/apikey).

### 2. Konfigurasi Lingkungan
Salin file `.env.example` menjadi `.env` lalu masukkan API Key Anda:
```bash
cp .env.example .env
```
Buka file `.env` dan ganti `your_gemini_api_key_here` dengan API key Anda:
```env
GEMINI_API_KEY=AIzaSy...
```

### 3. Instalasi Dependensi Python
Sangat disarankan menggunakan virtual environment:

```bash
# Buat virtual environment
python3 -m venv venv

# Aktifkan virtual environment
# Di macOS / Linux:
source venv/bin/activate
# Di Windows:
# .\venv\Scripts\activate

# Install dependensi
pip install -r requirements.txt
```

> **Tip:** Jika di Mac Anda belum memiliki Python / Xcode Command Line Tools, Anda bisa memasang `uv` (manajer Python super cepat) dengan perintah:
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> uv venv
> source .venv/bin/activate
> uv pip install -r requirements.txt
> ```

---

## 🎮 Cara Menjalankan

### Opsi A: Melalui Terminal CLI
```bash
python cli.py
```
Perintah praktis di dalam CLI:
- `/help`: Menampilkan panduan dan contoh pertanyaan
- `/reset`: Membersihkan memori percakapan untuk memulai topik baru
- `/docs`: Memuat ulang dokumen di folder `knowledge_base`
- `/exit`: Keluar dari program

### Opsi B: Melalui Web UI (Streamlit)
```bash
streamlit run web_ui.py
```
Aplikasi web akan terbuka otomatis di browser Anda di `http://localhost:8501`.

---

## 💡 Menambah Dokumen & Tool Baru

### Menambah Dokumen ke Knowledge Base
Cukup letakkan file `.md` atau `.txt` baru ke dalam folder `knowledge_base/`. Agent akan langsung bisa membaca dan mencari informasinya saat Anda menjalankan query!

### Menambah Tool Baru
Buka file [src/tools.py](file:///Users/karloindonesia/.gemini/antigravity/scratch/ai-agent-langgraph/src/tools.py), tambahkan fungsi baru dengan decorator `@tool`, lalu masukkan ke daftar `ALL_TOOLS`:
```python
from langchain_core.tools import tool

@tool
def custom_api_tool(param: str) -> str:
    """Deskripsi apa yang dilakukan tool ini agar agent tahu kapan harus memanggilnya."""
    # Logika tool Anda
    return "Hasil"
```

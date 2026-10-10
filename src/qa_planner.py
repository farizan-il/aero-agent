import json
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from src import config
from src.agent import extract_text_content


class QAPlanner:
    """Perencana QA cerdas ditenagai Gemini 3.8 Flash.
    Menganalisis arsitektur halaman dan menghasilkan matriks skenario pengujian komprehensif.
    """

    @classmethod
    def generate_test_plan(cls, page_inspection: Dict[str, Any], spec_context: str = "") -> List[Dict[str, Any]]:
        """Menghasilkan daftar skenario pengujian berjenjang (Happy Path, Negative, Boundary, Edge Cases)."""
        if not config.GEMINI_API_KEY:
            # Fallback test plan jika API key tidak tersedia
            return cls._get_default_test_plan(page_inspection)

        llm = ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.2,
        )

        prompt = f"""Anda adalah Senior QA Automation Architect (Aero QA Planner).
Tugas Anda adalah merancang matriks skenario pengujian web (Test Plan) berstandar industri 
berdasarkan struktur halaman yang terdeteksi dan spesifikasi dokumen (jika ada).

DATA HALAMAN WEB TARGET:
- URL: {page_inspection.get('url')}
- Judul: {page_inspection.get('title')}
- Headings: {page_inspection.get('headings')}
- Memerlukan Login: {page_inspection.get('is_auth_required')}
- Input Fields: {json.dumps(page_inspection.get('inputs', [])[:10], ensure_ascii=False)}
- Tombol/Navigasi: {json.dumps(page_inspection.get('buttons', [])[:10], ensure_ascii=False)}

KONTEKS DOKUMEN / SPESIFIKASI TAMBAHAN:
{spec_context[:1000] if spec_context else "Tidak ada dokumen spesifikasi tambahan. Analisis murni dari elemen halaman."}

INSTRUKSI:
Rancang 4 sampai 6 skenario pengujian yang paling krusial untuk halaman ini, mencakup:
1. Smoke & Page Health (Cek error konsol, HTTP status, kelengkapan elemen utama).
2. Happy Path User Flow (Skenario alur sukses end-user biasa).
3. Negative Testing / Validation (Form submit dengan data kosong atau email salah format).
4. Boundary & Edge Case (Input teks sangat panjang, karakter khusus, klik tombol ganda).

KEMBALIKAN HANYA ARRAY JSON VALID TANPA FORMAT MARKDOWN LAIN. Format setiap objek:
[
  {{
    "id": "TC-01",
    "category": "Smoke Test",
    "name": "Verifikasi Status Halaman & Error Konsol",
    "description": "Memeriksa bahwa halaman dapat dimuat tanpa adanya error JavaScript runtime di console.",
    "expected_result": "Halaman termuat sempurna dengan 0 error console.",
    "severity": "High"
  }},
  ...
]
"""

        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            cleaned = extract_text_content(response.content).strip()
            # Hapus backticks json bila ada
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            scenarios = json.loads(cleaned)
            if isinstance(scenarios, list) and len(scenarios) > 0:
                return scenarios
        except Exception as e:
            print(f"Warning: Gagal generate AI test plan: {e}. Menggunakan fallback.")

        return cls._get_default_test_plan(page_inspection)

    @staticmethod
    def _get_default_test_plan(page_inspection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Rencana pengujian dasar jika AI tidak tersedia atau offline."""
        title = page_inspection.get("title", "Halaman Web")
        has_inputs = page_inspection.get("inputs_count", 0) > 0

        plans = [
            {
                "id": "TC-01",
                "category": "Smoke Test",
                "name": "Integritas Pemuatan Halaman & Respon HTTP",
                "description": f"Memverifikasi status halaman '{title}' dan memastikan tidak ada HTTP 4xx/5xx.",
                "expected_result": "Status respons HTTP 200 OK dan judul halaman sesuai.",
                "severity": "Critical",
            },
            {
                "id": "TC-02",
                "category": "Console Audit",
                "name": "Audit Error Runtime JavaScript",
                "description": "Menyadap log konsol browser untuk memastikan tidak ada unhandled exception.",
                "expected_result": "Tidak ditemukan pesan error merah pada console log browser.",
                "severity": "High",
            },
        ]

        if has_inputs:
            plans.extend([
                {
                    "id": "TC-03",
                    "category": "Negative Test",
                    "name": "Validasi Form Input Kosong",
                    "description": "Mencoba submit form dengan mengosongkan seluruh kolom isian wajib.",
                    "expected_result": "Muncul pesan validasi error yang ramah pengguna, bukan crash.",
                    "severity": "Medium",
                },
                {
                    "id": "TC-04",
                    "category": "Boundary Test",
                    "name": "Uji Ketahanan Karakter Khusus & Batas Input",
                    "description": "Mengisi input teks dengan karakter khusus (<script>, kutip, tanda baca).",
                    "expected_result": "Sistem melakukan sanitasi input dengan aman tanpa XSS vulnerability.",
                    "severity": "High",
                },
            ])

        return plans

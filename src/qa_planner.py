import json
from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from src import config
from src.agent import extract_text_content
from src.persona_simulator import ALL_PERSONAS


class QAPlanner:
    """Perencana QA cerdas ditenagai Gemini 3.8 Flash.
    Merancang matriks skenario pengujian komprehensif berbasis simulasi beragam persona pengguna manusia.
    """

    @classmethod
    def generate_persona_test_plan(
        cls,
        page_inspection: Dict[str, Any],
        active_persona_codes: Optional[List[str]] = None,
        spec_context: str = "",
    ) -> List[Dict[str, Any]]:
        """Menghasilkan suite skenario pengujian realistis yang mencakup berbagai persona perilaku manusia."""
        selected_codes = active_persona_codes or list(ALL_PERSONAS.keys())
        selected_personas = [ALL_PERSONAS[c] for c in selected_codes if c in ALL_PERSONAS]

        persona_descriptions = "\n".join(
            [f"- **{p.name}** (`{p.code}`): {p.description} (Karakter: {', '.join(p.traits)})" for p in selected_personas]
        )

        if not config.GEMINI_API_KEY:
            return cls._get_default_multi_persona_plan(page_inspection, selected_personas)

        prompt = f"""Anda adalah Principal QA Automation Architect (Aero AI Lead).
Tugas Anda adalah merancang matriks pengujian (Test Suite) yang SANGAT DETAIL, REALISTIS, 
dan merefleksikan variasi perilaku manusia nyata saat menggunakan sistem website ini.

DATA HALAMAN WEB TARGET:
- URL: {page_inspection.get('url')}
- Judul: {page_inspection.get('title')}
- Headings: {page_inspection.get('headings')}
- Memerlukan Login: {page_inspection.get('is_auth_required')}
- Input Fields ({page_inspection.get('inputs_count')} elemen): {json.dumps(page_inspection.get('inputs', [])[:12], ensure_ascii=False)}
- Tombol/Navigasi: {json.dumps(page_inspection.get('buttons', [])[:12], ensure_ascii=False)}

PERSONA PENGGUNA YANG DIUJI:
{persona_descriptions}

KONTEKS SPESIFIKASI TAMBAHAN:
{spec_context[:1000] if spec_context else "Tidak ada dokumen spesifikasi tambahan."}

INSTRUKSI PENGUJIAN:
Buatlah antara 8 hingga 12 skenario pengujian komprehensif yang memetakan bagaimana masing-masing persona di atas akan berinteraksi dengan website ini:
1. Smoke & Web Vitals: Cek kecepatan render & ketiadaan JavaScript console errors.
2. Pengguna Normal: Alur sukses (Happy Path) dengan data valid.
3. Pengguna Terburu-buru (Impatient): Klik ganda cepat (Rage Click) pada tombol submit/navigasi untuk menguji debounce & race condition.
4. Pengguna Ceroboh (Clueless): Input salah format (email tanpa domain, spasi saja, format teks di kolom angka) dan verifikasi respon validasi.
5. Penguji Celah (Adversarial): Input ekstrem sangat panjang (>1000 char), payload probe sanitasi XSS (<script>), dan karakter khusus.
6. Pengguna Mobile: Uji layout di layar sempit smartphone (uji ketiadaan horizontal overflow).
7. Security & Accessibility Audit: Audit proteksi HTTPS, header keamanan, dan kelengkapan label aksesibilitas.

KEMBALIKAN HANYA ARRAY JSON VALID TANPA MARKDOWN LAIN. Format setiap objek:
[
  {{
    "id": "TC-01",
    "persona": "NORMAL",
    "category": "Smoke & Health",
    "name": "Verifikasi Status Halaman & Error Runtime",
    "description": "Memastikan halaman termuat sempurna tanpa error unhandled exception di console.",
    "expected_result": "Status 200 OK dan 0 error di JavaScript console.",
    "severity": "Critical"
  }},
  ...
]
"""

        models_to_try = [config.GEMINI_MODEL] + [m for m in config.FALLBACK_MODELS if m != config.GEMINI_MODEL]

        for candidate_model in models_to_try:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=candidate_model,
                    google_api_key=config.GEMINI_API_KEY,
                    temperature=0.25,
                )
                response = llm.invoke([HumanMessage(content=prompt)])
                cleaned = extract_text_content(response.content).strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

                scenarios = json.loads(cleaned)
                if isinstance(scenarios, list) and len(scenarios) >= 4:
                    return scenarios
            except Exception:
                continue

        return cls._get_default_multi_persona_plan(page_inspection, selected_personas)

    @staticmethod
    def _get_default_multi_persona_plan(page_inspection: Dict[str, Any], personas: List[Any]) -> List[Dict[str, Any]]:
        """Rencana pengujian bawaan multi-persona yang kaya jika offline."""
        title = page_inspection.get("title", "Halaman Web")
        has_inputs = page_inspection.get("inputs_count", 0) > 0

        plans = [
            {
                "id": "TC-01",
                "persona": "NORMAL",
                "category": "Smoke & Health",
                "name": f"Pemuatan Halaman '{title}' & Audit Konsol",
                "description": "Verifikasi status HTTP 200 dan ketiadaan error JavaScript console.",
                "expected_result": "Halaman termuat sempurna dengan 0 error runtime.",
                "severity": "Critical",
            },
            {
                "id": "TC-02",
                "persona": "NORMAL",
                "category": "Performance Audit",
                "name": "Audit Kecepatan Render (Core Web Vitals)",
                "description": "Memeriksa TTFB dan waktu total DOM Content Loaded.",
                "expected_result": "Waktu render di bawah 3000ms untuk pengalaman responsif.",
                "severity": "Medium",
            },
            {
                "id": "TC-03",
                "persona": "ADVERSARIAL",
                "category": "Security Headers Audit",
                "name": "Audit Header Keamanan (CSP, HSTS, X-Frame-Options)",
                "description": "Memeriksa ada tidaknya header keamanan untuk mitigasi serangan clickjacking dan injection.",
                "expected_result": "Header keamanan utama terpasang dengan skor minimal 60/100.",
                "severity": "High",
            },
            {
                "id": "TC-04",
                "persona": "MOBILE",
                "category": "Mobile Responsive Test",
                "name": "Uji Viewport Smartphone & Deteksi Horizontal Scroll Bug",
                "description": "Menguji halaman pada resolusi iPhone (393px) untuk mendeteksi layout overflow.",
                "expected_result": "Tidak ada elemen yang melebar keluar dari layar mobile.",
                "severity": "High",
            },
            {
                "id": "TC-05",
                "persona": "NORMAL",
                "category": "Accessibility (a11y)",
                "name": "Audit Aksesibilitas Gambar & Form Label",
                "description": "Memeriksa atribut alt pada tag <img> dan relasi label pada input form.",
                "expected_result": "Seluruh elemen penting memiliki label pendukung screen reader.",
                "severity": "Medium",
            },
        ]

        if has_inputs:
            plans.extend([
                {
                    "id": "TC-06",
                    "persona": "CLUELESS",
                    "category": "Validation Test",
                    "name": "Simulasi Pengguna Ceroboh: Submit Form Kosong",
                    "description": "Memicu submit form tanpa mengisi input wajib untuk melihat pesan validasi.",
                    "expected_result": "Muncul feedback error yang jelas, form tidak crash.",
                    "severity": "High",
                },
                {
                    "id": "TC-07",
                    "persona": "IMPATIENT",
                    "category": "Stress Test",
                    "name": "Simulasi Pengguna Terburu-buru: Rage Click Tombol Submit",
                    "description": "Melakukan klik 3x secara kilat (50ms interval) pada tombol aksi untuk menguji debounce.",
                    "expected_result": "Sistem mencegah pengiriman duplikat (no race condition).",
                    "severity": "High",
                },
                {
                    "id": "TC-08",
                    "persona": "ADVERSARIAL",
                    "category": "Boundary Test",
                    "name": "Simulasi Penguji Ekstrem: Uji Buffer Teks 1200+ Karakter",
                    "description": "Mengisi form input dengan teks sangat panjang untuk menguji batas alokasi memori UI.",
                    "expected_result": "Input terpotong aman atau menampilkan batas karakter maksimal.",
                    "severity": "Medium",
                },
                {
                    "id": "TC-09",
                    "persona": "ADVERSARIAL",
                    "category": "Security Sanity",
                    "name": "Simulasi Penguji Ekstrem: Probe Sanitasi Tag Script HTML",
                    "description": "Memasukkan tag <script> pada input teks untuk menguji sanitasi XSS dasar.",
                    "expected_result": "Karakter di-escape aman sebagai teks polos dan tidak dieksekusi browser.",
                    "severity": "Critical",
                },
            ])

        return plans

import json
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from src import config
from src.agent import extract_text_content


class FileAnalyzer:
    """Modul analisis file multi-format (PDF, Excel, CSV, JSON, TXT, MD).
    Mengekstrak spesifikasi, alur kerja sistem, atau data uji secara otomatis.
    """

    @staticmethod
    def read_file(file_path: Path) -> Dict[str, Any]:
        """Membaca isi file berdasarkan ekstensinya dan mengekstrak representasi teks & metadata."""
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File tidak ditemukan: {path}"}

        suffix = path.suffix.lower()
        filename = path.name

        try:
            if suffix in [".txt", ".md", ".log"]:
                text = path.read_text(encoding="utf-8", errors="ignore")
                return {
                    "success": True,
                    "filename": filename,
                    "type": "text",
                    "text": text,
                    "metadata": {"char_count": len(text), "lines": len(text.splitlines())},
                }

            elif suffix == ".json":
                raw_json = json.loads(path.read_text(encoding="utf-8"))
                formatted_text = json.dumps(raw_json, indent=2, ensure_ascii=False)
                return {
                    "success": True,
                    "filename": filename,
                    "type": "json",
                    "text": formatted_text,
                    "metadata": {"keys": list(raw_json.keys()) if isinstance(raw_json, dict) else len(raw_json)},
                }

            elif suffix in [".csv", ".tsv"]:
                sep = "\t" if suffix == ".tsv" else ","
                df = pd.read_csv(path, sep=sep)
                summary_text = (
                    f"CSV Dataset: {filename}\n"
                    f"Baris: {len(df)}, Kolom: {len(df.columns)} ({', '.join(df.columns)})\n\n"
                    f"Pratinjau 5 Baris Pertama:\n{df.head(5).to_string()}\n\n"
                    f"Statistik Deskriptif:\n{df.describe(include='all').to_string()}"
                )
                return {
                    "success": True,
                    "filename": filename,
                    "type": "tabular",
                    "text": summary_text,
                    "metadata": {"rows": len(df), "columns": list(df.columns)},
                }

            elif suffix in [".xlsx", ".xls"]:
                excel_file = pd.ExcelFile(path)
                sheets_data = []
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(path, sheet_name=sheet_name)
                    sheets_data.append(
                        f"--- Sheet: {sheet_name} (Baris: {len(df)}, Kolom: {len(df.columns)}) ---\n"
                        f"Kolom: {', '.join(df.columns)}\n"
                        f"Pratinjau Data:\n{df.head(5).to_string()}\n"
                    )
                combined_text = f"Excel Workbook: {filename}\n" + "\n".join(sheets_data)
                return {
                    "success": True,
                    "filename": filename,
                    "type": "excel",
                    "text": combined_text,
                    "metadata": {"sheets": excel_file.sheet_names},
                }

            elif suffix == ".pdf":
                reader = PdfReader(str(path))
                pages_text = []
                for idx, page in enumerate(reader.pages):
                    extracted = page.extract_text() or ""
                    if extracted.strip():
                        pages_text.append(f"--- Halaman {idx + 1} ---\n{extracted.strip()}")
                full_text = f"Dokumen PDF: {filename} (Total Halaman: {len(reader.pages)})\n\n" + "\n\n".join(pages_text)
                return {
                    "success": True,
                    "filename": filename,
                    "type": "pdf",
                    "text": full_text,
                    "metadata": {"pages": len(reader.pages)},
                }

            else:
                return {
                    "success": False,
                    "error": f"Format file '{suffix}' belum didukung. Gunakan PDF, CSV, Excel, TXT, MD, atau JSON.",
                }

        except Exception as e:
            return {"success": False, "error": f"Gagal membaca file {filename}: {str(e)}"}

    @classmethod
    def analyze_with_ai(cls, file_path: Path, prompt: str = "") -> str:
        """Mengirimkan konten file ke Gemini untuk dianalisis (ekstraksi skenario QA, bug, dsb)."""
        file_data = cls.read_file(file_path)
        if not file_data["success"]:
            return f"Error: {file_data['error']}"

        if not config.GEMINI_API_KEY:
            return f"File '{file_data['filename']}' berhasil dibaca ({file_data['type']}). Untuk analisis AI, silakan set GEMINI_API_KEY."

        llm = ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.2,
        )

        user_query = prompt or "Analisis dokumen ini secara komprehensif. Jelaskan alur kerja, fungsionalitas, entitas utama, serta potensi kasus uji (test case) yang relevan."

        system_instruction = (
            "Anda adalah AI QA & Business Analyst handal (Aero Analyst).\n"
            "Tugas Anda menganalisis file dokumen/data yang diberikan dan memberikan penjelasan "
            "yang sangat terstruktur, jelas, dan siap dijadikan acuan pengujian sistem atau pengambilan keputusan."
        )

        # Potong konten jika terlalu panjang (maksimum 40.000 karakter untuk keamanan context)
        raw_text = file_data["text"]
        if len(raw_text) > 40000:
            raw_text = raw_text[:40000] + "\n\n...[Konten dipotong karena batas panjang dokumen]..."

        full_prompt = f"{system_instruction}\n\nDokumen Target ({file_data['filename']}):\n{raw_text}\n\nPertanyaan/Instruksi Analisis:\n{user_query}"

        try:
            response = llm.invoke([HumanMessage(content=full_prompt)])
            return extract_text_content(response.content)
        except Exception as e:
            return f"Gagal memproses analisis AI: {str(e)}"

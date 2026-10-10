import os
import uuid
from pathlib import Path
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

import importlib
from src import config
importlib.reload(config)
from src.agent import build_agent, extract_text_content
from src.rag import rag_engine
from src.qa_runner import QARunner
from src.qa_reporter import QAReporter
from src.file_analyzer import FileAnalyzer

# Setup Halaman
st.set_page_config(
    page_title="Aero QA & AI Agent Studio",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🚀 Aero Agent — Autonomous QA & AI Studio")
st.caption("Platform AI Agent otonom: Otomatisasi Web QA/QC, Analisis Workflow & Dokumen, dan Asisten Percakapan Berbasis Gemini 3.8.")

# Sidebar Pengaturan
with st.sidebar:
    st.header("⚙️ Konfigurasi Sistem")
    api_key_input = st.text_input(
        "Google Gemini API Key",
        value=config.GEMINI_API_KEY if config.GEMINI_API_KEY != "your_gemini_api_key_here" else "",
        type="password",
        help="Dapatkan gratis di https://aistudio.google.com/app/apikey",
    )
    if api_key_input and api_key_input.strip() != config.GEMINI_API_KEY:
        config.GEMINI_API_KEY = api_key_input.strip()

    model_options = {
        "gemini-3.5-flash": "gemini-3.5-flash (Direkomendasikan - Kuota Tinggi)",
        "gemini-flash-latest": "gemini-flash-latest (Stabil)",
        "gemini-3.8-flash": "gemini-3.8-flash (Batas Kuota 20 Req/Hari)",
    }
    selected_model_key = st.selectbox(
        "Model Gemini",
        options=list(model_options.keys()),
        format_func=lambda k: model_options[k],
        index=0,
    )
    config.GEMINI_MODEL = selected_model_key

    st.markdown("---")
    st.subheader("🛠️ Kapabilitas Aero")
    st.markdown(
        """
        - 🧪 **Web QA Automation**: Simulasi alur end-user via Playwright.
        - 🔐 **Auth Handshake**: Kontrol izin & login interaktif.
        - 📄 **File Intelligence**: Analisis PRD/SOP, PDF, CSV, Excel.
        - 🔍 **RAG Knowledge Base**: Pencarian dokumen internal.
        - 🌐 **Live Web Search & Math Tool**.
        """
    )

    if st.button("🗑️ Reset Riwayat Chat"):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())[:8]
        st.rerun()

# Inisialisasi Tab Utama
tab_chat, tab_qa, tab_files = st.tabs([
    "💬 Asisten Percakapan (Chat)",
    "🧪 Web QA Automation Studio",
    "📄 File & Spec Intelligence",
])

# ==========================================
# TAB 1: ASISTEN PERCAKAPAN (CHAT)
# ==========================================
with tab_chat:
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())[:8]
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Tampilkan pesan riwayat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input obrolan
    if user_prompt := st.chat_input("Ketik pertanyaan, instruksi analisis, atau perintah QA..."):
        active_key = api_key_input.strip() or config.GEMINI_API_KEY
        if not active_key or active_key == "your_gemini_api_key_here":
            st.error("⚠️ Harap masukkan Google Gemini API Key di sidebar terlebih dahulu.")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            status_container = st.status("Aero Agent sedang memproses...", expanded=False)

            try:
                fallback_candidates = getattr(config, "FALLBACK_MODELS", ["gemini-3.5-flash", "gemini-flash-latest"])
                models_to_try = [config.GEMINI_MODEL] + [m for m in fallback_candidates if m != config.GEMINI_MODEL]
                executed = False
                final_content = ""

                for candidate_model in models_to_try:
                    try:
                        agent = build_agent(api_key=active_key, model=candidate_model)
                        thread_config = {"configurable": {"thread_id": st.session_state.thread_id}}

                        for event in agent.stream(
                            {"messages": [HumanMessage(content=user_prompt)]},
                            config=thread_config,
                            stream_mode="values",
                        ):
                            messages = event.get("messages", [])
                            if messages:
                                latest = messages[-1]
                                if hasattr(latest, "tool_calls") and latest.tool_calls:
                                    for tc in latest.tool_calls:
                                        status_container.write(f"🔧 Menjalankan tool: `{tc['name']}`")
                                if isinstance(latest, AIMessage) and latest.content:
                                    final_content = extract_text_content(latest.content)

                        executed = True
                        break
                    except Exception as err:
                        if "429" in str(err) or "RESOURCE_EXHAUSTED" in str(err):
                            status_container.write(f"⚠️ Kuota model `{candidate_model}` penuh. Beralih otomatis ke model alternatif...")
                            continue
                        raise err

                if executed:
                    status_container.update(label="Selesai!", state="complete", expanded=False)
                    message_placeholder.markdown(final_content)
                    st.session_state.messages.append({"role": "assistant", "content": final_content})
                else:
                    status_container.update(label="Gagal", state="error", expanded=True)
                    st.error("Semua model Gemini sedang mencapai batas kuota harian. Silakan coba kembali beberapa saat lagi.")

            except Exception as e:
                status_container.update(label="Terjadi kesalahan", state="error", expanded=True)
                st.error(f"Error: {str(e)}")

# ==========================================
# TAB 2: WEB QA AUTOMATION STUDIO
# ==========================================
with tab_qa:
    st.subheader("🧪 Autonomous Multi-Persona Web QA Studio")
    st.write("Aero menyimulasikan berbagai tipe perilaku manusia nyata saat menggunakan sistem: dari pengguna biasa, pengguna terburu-buru yang suka spam klik, pengguna ceroboh, hingga penguji celah keamanan dan pengguna smartphone.")

    col1, col2 = st.columns([3, 1])
    with col1:
        target_url = st.text_input("URL Website Target", placeholder="https://example.com atau localhost")
    with col2:
        browser_mode = st.selectbox("Mode Tampilan Browser", ["Headless (Latar Belakang)", "Tampilkan Browser (Visual)"])

    # Pilihan Persona Pengguna
    st.markdown("#### 👥 Pilih Persona Perilaku Pengguna untuk Diuji:")
    persona_options = {
        "NORMAL": "🟢 Normal / Ideal (Happy Path & valid flow)",
        "IMPATIENT": "⚡ Impatient (Rage clicker / Double submit spam)",
        "CLUELESS": "🤷 Clueless (Typo, salah format, spasi saja, form kosong)",
        "ADVERSARIAL": "🛡️ Adversarial (Batas teks 1200+ char, XSS sanitasi probe)",
        "MOBILE": "📱 Mobile User (Viewport iPhone 15 & overflow bug check)",
    }
    selected_personas = st.multiselect(
        "Persona Aktif:",
        options=list(persona_options.keys()),
        default=list(persona_options.keys()),
        format_func=lambda x: persona_options[x],
        help="Aero akan mengeksekusi skenario khusus berdasarkan kebiasaan setiap persona.",
    )

    # Opsi Autentikasi / Login Handshake
    with st.expander("🔐 Pengaturan Izin Autentikasi (Jika Website Butuh Login)"):
        st.info("Aero tidak akan mengakses data privat tanpa izin. Berikan akun uji jika halaman dilindungi login.")
        need_auth = st.checkbox("Website ini memerlukan login untuk diuji")
        auth_creds = None
        if need_auth:
            c_user, c_pass = st.columns(2)
            with c_user:
                auth_username = st.text_input("Username / Email Uji", placeholder="qa_tester@domain.com")
            with c_pass:
                auth_password = st.text_input("Password Uji", type="password")
            if auth_username and auth_password:
                auth_creds = {"username": auth_username, "password": auth_password}

    # Konteks Spesifikasi Tambahan
    with st.expander("📝 Fokus Alur Kerja Khusus (Opsional)"):
        custom_spec = st.text_area("Instruksi atau fokus workflow spesifik (misal: 'Fokus uji checkout keranjang belanja dan kolom voucher')")

    if st.button("🚀 Mulai Siklus Pengujian Multi-Persona", type="primary"):
        if not target_url.strip():
            st.warning("⚠️ Masukkan URL target terlebih dahulu.")
        elif not selected_personas:
            st.warning("⚠️ Pilih minimal satu persona pengguna.")
        else:
            is_headless = "Headless" in browser_mode
            import importlib
            import src.qa_runner
            importlib.reload(src.qa_runner)
            from src.qa_runner import QARunner
            qa_runner = QARunner(headless=is_headless)

            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(msg: str, pct: int):
                progress_bar.progress(pct)
                status_text.info(f"⏳ {msg}")

            with st.spinner("Aero sedang menjalankan simulasi multi-persona di browser..."):
                qa_result = qa_runner.run_qa_cycle(
                    url=target_url.strip(),
                    active_persona_codes=selected_personas,
                    spec_context=custom_spec,
                    auth_credentials=auth_creds,
                    progress_callback=update_progress,
                )

            progress_bar.progress(100)

            if not qa_result.get("success"):
                st.error(f"❌ Pengujian gagal: {qa_result.get('error')}")
            else:
                status_text.success("✅ Seluruh siklus pengujian multi-persona selesai dieksekusi!")

                # Kartu Metrik Utama
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Skor Lulus (Pass Rate)", f"{qa_result.get('pass_rate', 0)}%")
                m2.metric("Total Skenario Diuji", qa_result.get("total_cases", 0))
                m3.metric("Skenario Sukses", qa_result.get("passed_cases", 0))
                m4.metric("Durasi Eksekusi", f"{qa_result.get('duration', 0)}s")

                st.markdown("---")

                # Kartu Web Vitals & Keamanan
                c_vitals, c_sec, c_a11y = st.columns(3)
                with c_vitals:
                    perf = qa_result.get("performance_metrics", {})
                    st.markdown("##### ⚡ Core Web Vitals")
                    st.write(f"• **Waktu Load:** `{perf.get('load_time_ms', 0)} ms`")
                    st.write(f"• **TTFB:** `{perf.get('ttfb_ms', 0)} ms`")
                    st.write(f"• **Ukuran Transfer:** `{perf.get('transfer_size_kb', 0)} KB`")

                with c_sec:
                    sec = qa_result.get("security_audit", {})
                    st.markdown("##### 🛡️ Skor Keamanan Header")
                    sec_score = sec.get("security_score", 0)
                    st.write(f"• **Skor:** `{sec_score} / 100`")
                    st.write(f"• **HTTPS:** `{'✅ Aktif' if sec.get('is_https') else '❌ Non-HTTPS'}`")
                    st.write(f"• **CSP Header:** `{'✅ Ada' if sec.get('has_csp') else '⚠️ Belum Ada'}`")

                with c_a11y:
                    a11y = qa_result.get("accessibility_audit", {})
                    st.markdown("##### ♿ Aksesibilitas (a11y)")
                    st.write(f"• **Gambar Tanpa Alt:** `{a11y.get('missing_alt_images', 0)} item`")
                    st.write(f"• **Input Tanpa Label:** `{a11y.get('missing_labels', 0)} item`")
                    st.write(f"• **Mobile Viewport:** `{'✅ Sesuai' if a11y.get('has_viewport_meta') else '⚠️ Tidak Ada'}`")

                st.markdown("---")

                # Hasil Skenario Multi-Persona
                st.subheader("📋 Rincian Hasil Pengujian Skenario & Simulasi Persona")
                filter_status = st.radio("Filter Tampilan Status:", ["Semua", "Hanya Gagal & Warning", "Hanya Berhasil"], horizontal=True)

                for res in qa_result.get("test_results", []):
                    status = res.get("status")
                    if filter_status == "Hanya Gagal & Warning" and status == "PASS":
                        continue
                    if filter_status == "Hanya Berhasil" and status != "PASS":
                        continue

                    badge = "🟢 PASS" if status == "PASS" else ("🟡 WARNING" if status == "WARNING" else "🔴 FAIL")
                    persona_tag = f"[{res.get('persona', 'NORMAL')}]"

                    with st.expander(f"{badge} {persona_tag} {res.get('id')} — {res.get('name')} (Severity: {res.get('severity')})"):
                        st.write(f"**Persona:** `{res.get('persona')}` | **Kategori:** `{res.get('category')}`")
                        st.write(f"**Tujuan Pengujian:** {res.get('description')}")
                        st.write(f"**Kriteria Keberhasilan:** {res.get('expected_result')}")
                        st.write(f"**Hasil & Analisis:** {res.get('notes')}")

                        if res.get("reproduction_code"):
                            st.markdown("**Kode Reproduksi Bug (Playwright Python):**")
                            st.code(res.get("reproduction_code"), language="python")

                        if res.get("screenshot") and os.path.exists(res.get("screenshot")):
                            st.image(res.get("screenshot"), caption=f"Bukti Visual: {res.get('id')}")

                # Laporan Dokumen Lengkap
                report_md = QAReporter.generate_markdown_report(qa_result)
                st.markdown("---")
                st.download_button(
                    label="📥 Unduh Laporan Audit QA Lengkap (.md)",
                    data=report_md,
                    file_name=f"qa_report_{int(uuid.uuid4().hex[:6], 16)}.md",
                    mime="text/markdown",
                )

# ==========================================
# TAB 3: FILE & SPEC INTELLIGENCE
# ==========================================
with tab_files:
    st.subheader("📄 File & Specification Intelligence")
    st.write("Unggah dokumen spesifikasi sistem (PRD/SRS, SOP), dataset uji (CSV/Excel), atau file teks untuk dianalisis oleh Aero.")

    uploaded_file = st.file_uploader(
        "Pilih file (PDF, CSV, Excel, TXT, JSON, Markdown)",
        type=["pdf", "csv", "xlsx", "xls", "txt", "json", "md"],
    )

    if uploaded_file:
        # Simpan file sementara ke folder scratch
        upload_dir = config.BASE_DIR / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        saved_path = upload_dir / uploaded_file.name
        saved_path.write_bytes(uploaded_file.getbuffer())

        st.success(f"✓ File '{uploaded_file.name}' berhasil diunggah!")

        # Baca data awal
        file_info = FileAnalyzer.read_file(saved_path)
        if file_info["success"]:
            st.info(f"Format: **{file_info['type'].upper()}** | Metadata: `{file_info['metadata']}`")

            with st.expander("🔍 Pratinjau Teks Dokumen"):
                st.text(file_info["text"][:3000] + ("\n...[Lanjutan dipotong]" if len(file_info["text"]) > 3000 else ""))

            # Prompt Analisis AI
            st.markdown("---")
            file_prompt = st.text_input(
                "Instruksi Analisis Khusus",
                placeholder="Misal: 'Ekstraksi 5 skenario test case utama berdasarkan PRD ini' atau 'Rangkum alur kerjanya'",
            )

            if st.button("🧠 Jalankan Analisis AI pada File"):
                with st.spinner("Aero sedang membaca dan menganalisis dokumen..."):
                    ai_analysis = FileAnalyzer.analyze_with_ai(saved_path, file_prompt)
                st.markdown("### 📊 Hasil Analisis Aero Analyst:")
                st.markdown(ai_analysis)

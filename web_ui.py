import os
import uuid
from pathlib import Path
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

from src import config
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

    selected_model = st.selectbox(
        "Model Gemini",
        ["gemini-3.8-flash", "gemini-2.5-flash"],
        index=0,
    )
    config.GEMINI_MODEL = selected_model

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
                agent = build_agent(api_key=active_key)
                thread_config = {"configurable": {"thread_id": st.session_state.thread_id}}

                final_content = ""
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

                status_container.update(label="Selesai!", state="complete", expanded=False)
                message_placeholder.markdown(final_content)
                st.session_state.messages.append({"role": "assistant", "content": final_content})

            except Exception as e:
                status_container.update(label="Terjadi kesalahan", state="error", expanded=True)
                st.error(f"Error: {str(e)}")

# ==========================================
# TAB 2: WEB QA AUTOMATION STUDIO
# ==========================================
with tab_qa:
    st.subheader("🧪 Autonomous Web QA / QC Engine")
    st.write("Aero akan membuka website target, mempelajari struktur halamannya, merancang test matrix dengan berbagai skenario end-user, dan mencetak laporan audit lengkap.")

    col1, col2 = st.columns([3, 1])
    with col1:
        target_url = st.text_input("URL Website Target", placeholder="https://example.com atau localhost")
    with col2:
        browser_mode = st.selectbox("Mode Browser", ["Headless (Latar Belakang)", "Tampilkan Browser (Visual)"])

    # Opsi Autentikasi / Login Handshake
    with st.expander("🔐 Pengaturan Izin Autentikasi (Jika Website Butuh Login)"):
        st.info("Aero tidak akan mengakses akun tanpa izin. Jika website membutuhkan login, berikan kredensial uji coba di bawah ini.")
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
    with st.expander("📝 Catatan / Fokus Pengujian Khusus (Opsional)"):
        custom_spec = st.text_area("Instruksi atau fokus workflow spesifik (misal: 'Uji alur pendaftaran dan validasi form input')")

    if st.button("🚀 Mulai Siklus Pengujian QA Otonom", type="primary"):
        if not target_url.strip():
            st.warning("⚠️ Masukkan URL target terlebih dahulu.")
        else:
            is_headless = "Headless" in browser_mode
            qa_runner = QARunner(headless=is_headless)

            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(msg: str, pct: int):
                progress_bar.progress(pct)
                status_text.info(f"⏳ {msg}")

            with st.spinner("Menjalankan QA Automation Cycle..."):
                qa_result = qa_runner.run_qa_cycle(
                    url=target_url.strip(),
                    spec_context=custom_spec,
                    auth_credentials=auth_creds,
                    progress_callback=update_progress,
                )

            progress_bar.progress(100)

            if not qa_result.get("success"):
                st.error(f"❌ Pengujian gagal: {qa_result.get('error')}")
            else:
                status_text.success("✅ Seluruh siklus pengujian QA selesai dieksekusi!")

                # Kartu Metrik
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Skor Lulus (Pass Rate)", f"{qa_result.get('pass_rate', 0)}%")
                m2.metric("Total Skenario Diuji", qa_result.get("total_cases", 0))
                m3.metric("Skenario Sukses", qa_result.get("passed_cases", 0))
                m4.metric("Durasi Eksekusi", f"{qa_result.get('duration', 0)}s")

                st.markdown("---")

                # Hasil Skenario End-User
                st.subheader("📋 Rincian Hasil Eksekusi Skenario")
                for res in qa_result.get("test_results", []):
                    status = res.get("status")
                    badge = "🟢 PASS" if status == "PASS" else ("🟡 WARNING" if status == "WARNING" else "🔴 FAIL")
                    with st.expander(f"{badge} [{res.get('id')}] {res.get('name')} — Severity: {res.get('severity')}"):
                        st.write(f"**Kategori:** {res.get('category')}")
                        st.write(f"**Deskripsi:** {res.get('description')}")
                        st.write(f"**Kriteria Hasil:** {res.get('expected_result')}")
                        st.write(f"**Temuan Aktual:** {res.get('notes')}")
                        if res.get("screenshot") and os.path.exists(res.get("screenshot")):
                            st.image(res.get("screenshot"), caption=f"Bukti Eksekusi: {res.get('id')}")

                # Laporan Dokumen Lengkap
                report_md = QAReporter.generate_markdown_report(qa_result)
                st.markdown("---")
                st.download_button(
                    label="📥 Unduh Laporan QA Lengkap (.md)",
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

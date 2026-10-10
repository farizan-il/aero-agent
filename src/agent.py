from typing import Dict, Any, Generator, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from src import config
from src.tools import ALL_TOOLS

SYSTEM_PROMPT = """Anda adalah asisten AI cerdas dan QA Automation Engineer handal (Aero Agent).
Tugas Anda adalah membantu pengguna menjawab pertanyaan, menyelesaikan tugas, menganalisis dokumen/file, serta melakukan pengujian kualitas website (QA/QC Automation).

Panduan Kerja:
1. **QA Website Automation**:
   - Jika pengguna meminta menguji website, mencari bug, atau melakukan audit web, gunakan tool `run_website_qa_audit`.
   - Selalu perhatikan apakah website target membutuhkan login/autentikasi dan mintalah izin kredensial jika diperlukan.

2. **Analisis File Dokumen & Data**:
   - Jika pengguna menyebutkan file lokal atau ingin membaca dokumen spesifikasi (PDF, CSV, Excel, TXT, JSON), gunakan tool `analyze_document_file`.

3. **Knowledge Base Internal**:
   - Jika pengguna menanyakan tentang produk, harga, kebijakan internal, atau SLA, gunakan tool `search_knowledge_base`.

4. **Web Search & Kalkulator**:
   - Gunakan `web_search` untuk info publik eksternal, dan `calculate` untuk perhitungan matematika akurat.

5. **Gaya Komunikasi**:
   - Bersikap profesional, analitis, terstruktur (gunakan bullet points atau markdown).
"""


def build_agent(api_key: Optional[str] = None, model: Optional[str] = None, *args, **kwargs):
    """Membangun graph agent LangGraph yang terintegrasi dengan Google Gemini dan Memory checkpointer."""
    key = api_key or config.GEMINI_API_KEY
    if not key:
        raise ValueError("GEMINI_API_KEY belum disetel. Harap masukkan API key di file .env")

    model_name = model or config.GEMINI_MODEL
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=key,
        temperature=config.AGENT_TEMPERATURE,
    )

    memory = MemorySaver()

    # create_react_agent mendukung parameter 'prompt' pada LangGraph versi terbaru
    # atau 'state_modifier' pada versi sebelumnya.
    try:
        agent = create_react_agent(
            model=llm,
            tools=ALL_TOOLS,
            checkpointer=memory,
            prompt=SYSTEM_PROMPT,
        )
    except TypeError:
        # Fallback untuk versi LangGraph yang memakai state_modifier
        agent = create_react_agent(
            model=llm,
            tools=ALL_TOOLS,
            checkpointer=memory,
            state_modifier=SYSTEM_PROMPT,
        )

    return agent


def extract_text_content(content: Any) -> str:
    """Mengekstrak teks murni yang bersih dari respons Gemini.
    Menyaring metadata teknis seperti signature, extras, dan nested dictionaries.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text" and "text" in part:
                    texts.append(part["text"])
                elif "text" in part and not part.get("type") == "thought":
                    texts.append(part["text"])
            elif isinstance(part, str):
                texts.append(part)
        return "".join(texts)
    return str(content) if content is not None else ""


def ask_agent(agent, user_input: str, thread_id: str = "default_session") -> str:
    """Mengirim pesan ke agent dengan context memory tersimpan berdasarkan thread_id."""
    thread_config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=user_input)]}

    response = agent.invoke(inputs, config=thread_config)
    messages = response.get("messages", [])
    if messages:
        return extract_text_content(messages[-1].content)
    return "Maaf, tidak ada respon dari agent."


def stream_agent_steps(agent, user_input: str, thread_id: str = "default_session") -> Generator[Dict[str, Any], None, None]:
    """Streaming generator yang mengirimkan setiap event (tool calls, respons) secara real-time."""
    thread_config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=user_input)]}

    for event in agent.stream(inputs, config=thread_config, stream_mode="values"):
        messages = event.get("messages", [])
        if messages:
            latest = messages[-1]
            yield {
                "type": latest.__class__.__name__,
                "content": extract_text_content(getattr(latest, "content", "")),
                "tool_calls": getattr(latest, "tool_calls", None),
            }


def stream_agent_tokens(agent, user_input: str, thread_id: str = "default_session") -> Generator[Dict[str, Any], None, None]:
    """Streaming generator token-by-token dan tool calls secara real-time untuk latensi instan."""
    thread_config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=user_input)]}

    for item in agent.stream(inputs, config=thread_config, stream_mode="messages"):
        msg = item[0] if isinstance(item, tuple) else item
        msg_type = msg.__class__.__name__

        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                yield {
                    "type": "tool_call",
                    "name": tc.get("name", "tool"),
                    "args": tc.get("args", {}),
                }
        elif hasattr(msg, "content") and msg.content:
            if "AIMessage" in msg_type:
                clean_text = extract_text_content(msg.content)
                if clean_text:
                    yield {"type": "token", "text": clean_text}
            elif "ToolMessage" in msg_type:
                yield {
                    "type": "tool_result",
                    "name": getattr(msg, "name", "tool"),
                }


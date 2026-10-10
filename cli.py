import sys
import uuid
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

from src import config
from src.agent import build_agent, ask_agent, stream_agent_tokens
from src.rag import rag_engine

console = Console()


def print_banner():
    console.print(
        Panel.fit(
            "[bold cyan]🚀 Aero Agent[/bold cyan] - Powered by [bold yellow]Google Gemini[/bold yellow]\n"
            "[green]Fitur:[/green] RAG Knowledge Base • Multi-Tool Calling • Conversational Memory\n"
            "[dim]Ketik [bold]/help[/bold] untuk menu bantuan, atau [bold]exit[/bold] untuk keluar.[/dim]",
            border_style="cyan",
            title="Aero Agent (LangGraph)",
        )
    )


def show_help():
    console.print(
        Panel(
            "[bold]Perintah Tersedia:[/bold]\n"
            "• [cyan]/reset[/cyan] - Hapus memori percakapan dan mulai sesi baru\n"
            "• [cyan]/docs[/cyan]  - Muat ulang dokumen di folder knowledge_base\n"
            "• [cyan]/info[/cyan]  - Lihat konfigurasi model dan tools aktif\n"
            "• [cyan]/exit[/cyan]  - Keluar dari program\n\n"
            "[bold]Contoh Pertanyaan yang Bisa Dicoba:[/bold]\n"
            "1. [italic]\"Apa saja paket harga untuk NusantaAgent dan berapa SLA responnya?\"[/italic] (Menguji RAG)\n"
            "2. [italic]\"Jika saya ambil paket Pro 1 tahun dengan diskon 15%, berapa total biayanya?\"[/italic] (Menguji Calculate)\n"
            "3. [italic]\"Hari dan jam berapa sekarang?\"[/italic] (Menguji Time Tool)\n"
            "4. [italic]\"Siapa penemu bahasa pemrograman Python?\"[/italic] (Menguji Web Search)",
            title="Panduan Penggunaan",
            border_style="blue",
        )
    )


def main():
    print_banner()

    # Validasi API Key
    missing = config.validate_config()
    if missing:
        console.print("[bold red]⚠️  Perhatian:[/bold red] API Key Gemini belum terkonfigurasi!")
        console.print("Silakan masukkan Google Gemini API Key Anda:")
        console.print("[dim](Dapatkan gratis di https://aistudio.google.com/app/apikey)[/dim]")
        user_key = Prompt.ask("[yellow]Gemini API Key[/yellow]", password=True)
        if not user_key.strip():
            console.print("[red]API key tidak boleh kosong. Keluar...[/red]")
            sys.exit(1)
        config.GEMINI_API_KEY = user_key.strip()

        # Simpan otomatis ke file .env
        try:
            env_file = config.BASE_DIR / ".env"
            if env_file.exists():
                text = env_file.read_text()
                import re
                if "GEMINI_API_KEY=" in text:
                    text = re.sub(r"GEMINI_API_KEY=.*", f"GEMINI_API_KEY={config.GEMINI_API_KEY}", text)
                else:
                    text += f"\nGEMINI_API_KEY={config.GEMINI_API_KEY}\n"
                env_file.write_text(text)
                console.print("[dim green]✓ API Key tersimpan di file .env[/dim green]")
        except Exception:
            pass

    # Inisialisasi knowledge base
    console.print("\n[yellow]⏳ Memuat dokumen knowledge base...[/yellow]")
    count = rag_engine.load_documents()
    console.print(f"[green]✓ Berhasil memuat {count} potongan dokumen internal.[/green]\n")

    # Inisialisasi Agent
    try:
        with console.status("[cyan]Membangun alur kerja LangGraph Agent...[/cyan]"):
            agent = build_agent(config.GEMINI_API_KEY)
        console.print("[bold green]✓ Agent siap digunakan![/bold green]\n")
    except Exception as e:
        console.print(f"[bold red]Gagal menginisialisasi agent:[/bold red] {e}")
        sys.exit(1)

    thread_id = str(uuid.uuid4())[:8]

    while True:
        try:
            user_input = Prompt.ask(f"[bold green]Anda ({thread_id})[/bold green]").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "/exit", "keluar"]:
                console.print("[cyan]Sampai jumpa kembali! 👋[/cyan]")
                break

            if user_input.lower() == "/help":
                show_help()
                continue

            if user_input.lower() == "/reset":
                thread_id = str(uuid.uuid4())[:8]
                console.print(f"[yellow]✓ Memori percakapan di-reset. Sesi baru: {thread_id}[/yellow]")
                continue

            if user_input.lower() == "/docs":
                count = rag_engine.load_documents()
                console.print(f"[green]✓ Dokumen di-refresh: {count} potongan termuat.[/green]")
                continue

            if user_input.lower() == "/info":
                console.print(
                    Panel(
                        f"• Model: [cyan]{config.GEMINI_MODEL}[/cyan]\n"
                        f"• Embeddings: [cyan]{config.EMBEDDING_MODEL}[/cyan]\n"
                        f"• Knowledge Base Dir: [cyan]{config.KNOWLEDGE_BASE_DIR}[/cyan]\n"
                        f"• Tools: [green]search_knowledge_base, web_search, calculate, get_current_time[/green]\n"
                        f"• Sesi ID: [yellow]{thread_id}[/yellow]",
                        title="Info Konfigurasi",
                    )
                )
                continue

            # Eksekusi agent secara real-time streaming
            console.print("\n[bold cyan]Aero Agent:[/bold cyan] ", end="")
            for event in stream_agent_tokens(agent, user_input, thread_id=thread_id):
                event_type = event.get("type")
                if event_type == "tool_call":
                    tool_name = event["name"]
                    console.print(f"\n[dim yellow]⚡ [Tool: {tool_name}...][/dim yellow]")
                elif event_type == "tool_result":
                    console.print(f"[dim green]✓ Selesai[/dim green]")
                    console.print("[bold cyan]Aero Agent:[/bold cyan] ", end="")
                elif event_type == "token":
                    sys.stdout.write(event["text"])
                    sys.stdout.flush()

            console.print("\n")

        except KeyboardInterrupt:
            console.print("\n[cyan]Sesi dihentikan. Sampai jumpa! 👋[/cyan]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Terjadi kesalahan:[/bold red] {e}\n")


if __name__ == "__main__":
    main()

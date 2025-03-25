from datetime import datetime
from typing import List, Optional, Dict, Any
import click
import logging
import json
from rich.console import Console
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import Style

from .providers import PROVIDERS
from .providers.base import Message
from .providers.prompts import Prompts
from .utils.io_utils import (
    format_prompt_with_context,
    read_directory,
    setup_logging,
    LOGS_PATH,
    get_provider_and_model,
)
from rich.table import Table
from rich.live import Live

# Type aliases for better code readability
FileContext = str
MessageHistory = List[Message]
PromptType = str


class ChatSession:
    """Manages an interactive chat session with an LLM."""

    def __init__(
        self,
        provider: str,
        model: str,
        file_context: FileContext = "",
        vibe: Optional[str] = None,
    ):
        self.console = Console()
        self.provider_cls = PROVIDERS[provider]
        self.llm = self.provider_cls(model=model)
        self.file_context = file_context
        self.message_history: MessageHistory = []
        self.prompt_type = self._get_prompt_type(vibe)
        self.session = self._setup_prompt_session()

    def _get_prompt_type(self, vibe: Optional[str]) -> PromptType:
        """Determine the prompt type based on the vibe setting."""
        if not vibe:
            return Prompts.REPL

        prompt_types = {"primer": Prompts.UNIVERSAL_PRIMER, "concise": Prompts.CONCISE}
        return prompt_types.get(vibe, Prompts.REPL)

    def _setup_prompt_session(self) -> PromptSession:
        """Set up the prompt session with custom key bindings."""
        kb = KeyBindings()

        @kb.add(Keys.Enter)
        def _(event):
            event.current_buffer.validate_and_handle()

        @kb.add("escape", "enter")
        def _(event):
            event.current_buffer.insert_text("\n")

        return PromptSession(key_bindings=kb)

    def _handle_user_input(self, user_input: str) -> bool:
        """Process user input and return whether to continue the session."""
        if user_input.lower() in ["exit", "quit"]:
            self.console.print("[bold blue]Ending chat session[/]")
            return False

        try:
            formatted_prompt = format_prompt_with_context(user_input, self.file_context)
            response = ""

            with Live(
                Markdown(response),
                console=self.console,
                auto_refresh=True,
                screen=False,
            ) as live:
                for token in self.llm.query_stream(
                    prompt=formatted_prompt,
                    prompt_type=self.prompt_type,
                    message_history=self.message_history,
                ):
                    response += token
                    live.update(Markdown(response))

            if response:
                logging.info({"query": formatted_prompt, "response": response})
                self.message_history.append(Message("user", formatted_prompt))
                self.message_history.append(Message("assistant", response))

            return True

        except Exception as e:
            self.console.print(f"[bold red]Error: {str(e)}[/]")
            return True

    def run(self) -> None:
        """Run the chat session."""
        self.console.print(
            "[bold blue]Chat session started. Type 'exit' to end the conversation.[/]"
        )

        while True:
            try:
                user_input = self.session.prompt("\n>>> ")
                if not self._handle_user_input(user_input):
                    break

            except (click.exceptions.Abort, EOFError):
                self.console.print("[bold blue]Goodbye![/]")
                break


class HistoryViewer:
    """Handles viewing chat history with rich formatting."""

    def __init__(self, n: Optional[int] = None):
        self.n = n
        self.console = Console()

    def _get_log_entries(self) -> List[Dict[str, Any]]:
        """Retrieve log entries from the log file."""
        curr_year, curr_month = datetime.now().year, datetime.now().month
        file_name = LOGS_PATH / f"llm_cli_{str(curr_year)}{curr_month:02}.log"

        try:
            with open(file_name, "r", encoding="utf-8") as f:
                log_entries = [json.loads(line) for line in f.readlines()]
                if self.n:
                    return log_entries[-self.n :]
                return log_entries[-10:]
        except FileNotFoundError:
            self.console.print("[bold red]No log file found.[/]")
            return []

    def display(self) -> None:
        """Display the chat history in a formatted table."""
        log_entries = self._get_log_entries()

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Timestamp", style="dim")
        table.add_column("Level", style="bold")
        table.add_column("Query", style="dim")
        table.add_column("Response", style="bold")

        for entry in log_entries:
            table.add_row(
                entry.get("timestamp", "N/A"),
                entry.get("level", "N/A"),
                entry.get("query", "N/A"),
                entry.get("response", "N/A"),
            )

        self.console.print(table)


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("-f", "--files", help="Files to use as context", multiple=True)
@click.option(
    "-d",
    "--directory",
    help="Directory to use as context, use . for current dir",
    multiple=True,
)
@click.option(
    "-v",
    "--vibe",
    help="vibe used for the prompt types, available now: 'primer', 'concise'",
)
@click.option("-p", "--provider", help="LLM provider to use")
@click.option(
    "-m",
    "--model",
    help="Model to use (e.g., claude-3-7-sonnet-20250219, gemini-1.5-pro)",
)
def cli(
    ctx: click.Context,
    files: Optional[List[str]],
    directory: Optional[List[str]],
    vibe: Optional[str],
    provider: Optional[str],
    model: Optional[str],
) -> None:
    """Main CLI entry point."""
    provider, model = get_provider_and_model(provider, model)
    ctx.ensure_object(dict)
    ctx.obj["provider"] = provider
    ctx.obj["model"] = model

    if ctx.invoked_subcommand is None:
        ctx.invoke(chat, files=files, directory=directory, vibe=vibe)


@cli.command()
@click.option("-f", "--files", help="File to use as context", multiple=True)
@click.option(
    "-d",
    "--directory",
    help="Directory to use as context, use . for current dir",
    multiple=True,
)
@click.option(
    "-v",
    "--vibe",
    help="vibe used for the prompt types, available now: 'primer', 'concise'",
)
@click.pass_context
def chat(
    ctx: click.Context,
    files: Optional[List[str]],
    directory: Optional[List[str]],
    vibe: Optional[str],
) -> None:
    """Start an interactive chat session with the LLM."""
    setup_logging()

    file_context = ""
    if files:
        for file in files:
            try:
                with open(file, "r") as f:
                    file_context += f.read()
            except FileNotFoundError:
                click.echo(f"Warning: File {file} not found")

    if directory:
        for d in directory:
            file_context += read_directory(d)

    chat_session = ChatSession(
        provider=ctx.obj["provider"],
        model=ctx.obj["model"],
        file_context=file_context,
        vibe=vibe,
    )
    chat_session.run()


@cli.command()
@click.option("-n", help="Show the last N logs")
def history(n: Optional[int]) -> None:
    """View chat history with rich formatting."""
    viewer = HistoryViewer(n)
    viewer.display()


if __name__ == "__main__":
    # Click will automatically parse command line args,
    # so we only need to pass the obj parameter
    cli(obj={})

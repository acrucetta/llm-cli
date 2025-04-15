import json
from rich.table import Table
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..providers import PROVIDERS
from ..providers.base import Message
from ..providers.prompts import Prompts
from ..utils.io_utils import LOGS_PATH, format_prompt_with_context


import click
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

import logging

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
        prompt_types = {"primer": Prompts.UNIVERSAL_PRIMER, "concise": Prompts.CONCISE}
        if vibe is None:
            return Prompts.REPL
        return prompt_types.get(vibe.lower(), Prompts.REPL)

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
        self.n = int(n) if n else None
        self.console = Console()

    def _get_log_entries(self) -> List[Dict[str, Any]]:
        """Retrieve log entries from the log file."""
        curr_year, curr_month = datetime.now().year, datetime.now().month
        file_name = LOGS_PATH / f"llm_cli_{str(curr_year)}{curr_month:02}.log"

        try:
            with open(file_name, "r", encoding="utf-8") as f:
                log_entries = [json.loads(line) for line in f.readlines()]
                if self.n is not None:
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

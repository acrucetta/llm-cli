from typing import List, Optional
import click
import logging
from prompt_toolkit.styles import Style

from .chat.chat import ChatSession, HistoryViewer

from .providers.base import Message
from .utils.io_utils import (
    read_directory,
    setup_logging,
    get_provider_and_model,
)


@click.group()
def cli():
    pass


@click.command()
@click.option("-p", "--provider", help="LLM provider to use")
@click.option(
    "-m",
    "--model",
    help="Model to use (e.g., claude-3-7-sonnet-20250219, gemini-1.5-pro)",
)
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
def chat(
    provider: Optional[str],
    model: Optional[str],
    files: Optional[List[str]],
    directory: Optional[List[str]],
    vibe: Optional[str],
) -> None:
    """Start an interactive chat session with the LLM."""
    setup_logging()
    provider, model = get_provider_and_model(provider, model)

    # Use vibe from context if not provided directly
    logging.info(f"Using vibe: {vibe}")

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
        provider=provider,
        model=model,
        file_context=file_context,
        vibe=vibe,
    )
    chat_session.run()


@click.command()
@click.option("-n", help="Show the last N logs")
def history(n: Optional[int]) -> None:
    """View chat history with rich formatting."""
    viewer = HistoryViewer(n)
    viewer.display()


cli.add_command(chat)
cli.add_command(history)

if __name__ == "__main__":
    cli()

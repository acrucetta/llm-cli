from datetime import datetime
import click
import logging
import json
from rich.console import Console
from rich.markdown import Markdown
from .providers import PROVIDERS
from .providers.base import Message
from .providers.prompts import Prompts
from .utils.io_utils import (
    format_prompt_with_context,
    read_directory,
    setup_logging,
    LOGS_PATH,
    load_config,
)
from rich.table import Table
from rich.live import Live


def get_provider_and_model(provider=None, model=None):
    """Get the provider and model, using defaults from config when needed."""
    config = load_config()

    # Determine provider
    provider = provider or config["provider"]
    if provider not in PROVIDERS:
        raise click.UsageError(f"Provider {provider} not supported")

    # Determine model
    if not model:
        # If no model specified, use the default for the selected provider
        model = config["provider_defaults"].get(provider)

    return provider, model


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("-p", "--prompt-text", help="One-off prompt to send to the LLM")
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
@click.option("--provider", help="LLM provider to use")
@click.option(
    "-m",
    "--model",
    help="Model to use (e.g., claude-3-7-sonnet-20250219, gemini-1.5-pro)",
)
def cli(
    ctx, prompt_text, files=None, directory=None, vibe=None, provider=None, model=None
):
    # Store provider and model in context for subcommands
    provider, model = get_provider_and_model(provider, model)
    ctx.ensure_object(dict)
    ctx.obj["provider"] = provider
    ctx.obj["model"] = model

    if ctx.invoked_subcommand is None:
        # If no subcommand is called, default to chat
        if prompt_text:
            # One-off prompt with -p flag
            ctx.invoke(
                ask,
                prompt=prompt_text,
                files=files,
                directory=directory,
                vibe=vibe,
            )
        else:
            # Start chat with no initial prompt
            ctx.invoke(
                chat,
                initial_prompt=None,
                files=files,
                directory=directory,
                vibe=vibe,
            )


@cli.command()
@click.argument("prompt")
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
@click.pass_context
def ask(ctx, prompt, files, directory, vibe):
    """Ask a quick question"""
    setup_logging()

    provider_cls = PROVIDERS[ctx.obj["provider"]]
    llm = provider_cls(model=ctx.obj["model"])

    file_context = ""
    if files:
        for file in files:
            with open(file, "r") as f:
                file_context += f.read()

    if directory:
        for d in directory:
            file_context += read_directory(d)

    prompt_type = Prompts.MAIN
    if vibe:
        if vibe == "primer":
            prompt_type = Prompts.UNIVERSAL_PRIMER
        elif vibe == "concise":
            prompt_type = Prompts.CONCISE
        else:
            click.echo("Couldn't find the given prompt, using the default one.")

    formatted_prompt = format_prompt_with_context(prompt, file_context)
    console = Console()
    buffer = ""

    # Initialize Live context with empty Markdown
    with Live(
        Markdown(buffer), console=console, auto_refresh=True, screen=False
    ) as live:
        for token in llm.query_stream(formatted_prompt, prompt_type=prompt_type):
            buffer += token
            # Update the Live display with the new Markdown content
            live.update(Markdown(buffer))

    # Log the complete interaction
    response = str(buffer)
    logging.info({"query": formatted_prompt, "response": response})


@cli.command()
@click.option("-f", "--files", help="File to use as context", multiple=True)
@click.option(
    "-d",
    "--directory",
    help="Directory to use as context, use . for current dir",
    multiple=True,
)
@click.option(
    "--initial-prompt", help="Initial prompt to start the chat with", required=False
)
@click.option(
    "-v",
    "--vibe",
    help="vibe used for the prompt types, available now: 'primer', 'concise'",
)
@click.pass_context
def chat(ctx, files, directory, initial_prompt=None, vibe=None):
    """Start an interactive chat session with the LLM."""
    setup_logging()

    provider_cls = PROVIDERS[ctx.obj["provider"]]
    llm = provider_cls(model=ctx.obj["model"])

    file_context = ""
    if files:
        for file in files:
            with open(file, "r") as f:
                file_context += f.read()

    if directory:
        for d in directory:
            file_context += read_directory(d)

    prompt_type = Prompts.REPL
    if vibe:
        if vibe == "primer":
            prompt_type = Prompts.UNIVERSAL_PRIMER
        elif vibe == "concise":
            prompt_type = Prompts.CONCISE
        else:
            click.echo("Couldn't find the given prompt, using the default one.")
            
    console = Console()
    message_history = []
    console.print(
        "[bold blue]Chat session started. Type 'exit' to end the conversation.[/]"
    )

    # Handle initial prompt if provided
    if initial_prompt:
        formatted_prompt = format_prompt_with_context(initial_prompt, file_context)
        response = ""
        console.print("\n[bold green]Initial prompt:[/] " + initial_prompt)

        with Live(
            Markdown(response), console=console, auto_refresh=True, screen=False
        ) as live:
            for token in llm.query_stream(
                prompt=formatted_prompt,
                prompt_type=prompt_type,
                message_history=message_history,
            ):
                response += token
                live.update(Markdown(response))

        if response:
            logging.info({"query": formatted_prompt, "response": response})
            message_history.append(Message("user", formatted_prompt))
            message_history.append(Message("assistant", response))

    while True:
        try:
            user_input = click.prompt("\n>>>", type=str)

            if user_input.lower() in ["exit", "quit"]:
                console.print("[bold blue]Ending chat session[/]")
                break

            formatted_prompt = format_prompt_with_context(user_input, file_context)
            response = ""
            with Live(
                Markdown(response), console=console, auto_refresh=True, screen=False
            ) as live:
                for token in llm.query_stream(
                    prompt=formatted_prompt,
                    prompt_type=prompt_type,
                    message_history=message_history,
                ):
                    response += token
                    live.update(Markdown(response))

            if response:
                logging.info({"query": formatted_prompt, "response": response})
                message_history.append(Message("user", formatted_prompt))
                message_history.append(Message("assistant", response))

        except click.exceptions.Abort:  # Handles Ctrl+C
            console.print("[bold blue] Goodbye! ")
            return
        except EOFError:  # Handles Ctrl+D
            console.print("[bold blue] Goodbye! ")
            return
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/]")
            continue


@cli.command()
@click.option("-n", help="Show the last N logs")
def history(n):
    """See your chat history"""
    curr_year, curr_month = datetime.now().year, datetime.now().month
    file_name = LOGS_PATH / f"llm_cli_{str(curr_year)}{curr_month:02}.log"
    with open(file_name, "r", encoding="utf-8") as f:
        log_entries = f.readlines()
        if n:
            log_entries = log_entries[-int(n) :]
        else:
            log_entries = log_entries[-10:]

        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Timestamp", style="dim")
        table.add_column("Level", style="bold")
        table.add_column("Query", style="dim")
        table.add_column("Response", style="bold")

        for log_entry in log_entries:
            log_dict = json.loads(log_entry)
            query = log_dict.get("query", "N/A")
            response = log_dict.get("response", "N/A")
            timestamp = log_dict.get("timestamp", "N/A")
            level = log_dict.get("level", "N/A")
            table.add_row(timestamp, level, query, response)

        console.print(table)


if __name__ == "__main__":
    cli(obj={})  # Initialize the context object

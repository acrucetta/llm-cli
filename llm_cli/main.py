from datetime import datetime
import hashlib
import os
import click
import logging
import json
from rich.console import Console
from rich.markdown import Markdown

from .providers import PROVIDERS
from .providers.base import Message
from .providers.prompts import Prompts
from .utils.embeddings import build_codebase_index, retrieve_relevant_chunks
from .utils.io_utils import (
    load_config,
    read_directory,
    setup_logging,
    save_config,
    LOGS_PATH,
)
from rich.table import Table
from rich.live import Live


@click.group()
def cli():
    pass


@cli.command()
@click.argument("prompt")
@click.option("--provider", help="LLM provider to use")
@click.option("--model", help="Model to use")
@click.option("-f", "--files", help="Files to use as context", multiple=True)
@click.option("-d", "--dir", help="Directory to use as context, use . for current dir")
@click.option(
    "-t",
    "--tag",
    help="Tag used for the prompt types, available now: 'primer', 'concise'",
)
@click.option("-c", "--codebase", help="Path to codebase to index and use as context")
def ask(prompt, provider, model, files, dir, tag, codebase):
    """Ask a quick question"""
    config = load_config()
    setup_logging()
    provider = provider or config["provider"]
    model = model or config.get("model")

    if provider not in PROVIDERS:
        click.echo(f"Error: Provider {provider} not supported")
        return

    provider_cls = PROVIDERS[provider]
    llm = provider_cls(model=model)

    file_context = ""

    if files:
        for file in files:
            with open(file, "r") as f:
                file_context += f.read()

    if dir:
        file_context += read_directory(dir)

    if codebase:
        # The name or path of the index file can be something like .cache/<hash_of_codebase>.pkl
        # so that if the codebase path is the same, we reuse the same index.
        # We'll just do a simple hash for uniqueness:
        codebase_hash = hashlib.md5(codebase.encode("utf-8")).hexdigest()
        index_path = os.path.join(".cache", f"codebase_index_{codebase_hash}.pkl")
        os.makedirs(".cache", exist_ok=True)

        # Build or load index
        index = build_codebase_index(codebase, index_path)

        # Retrieve top chunks for the user's query
        relevant_chunks = retrieve_relevant_chunks(prompt, index, top_k=3)

        # Add them to the file_context
        for chunk in relevant_chunks:
            print("Adding chunk from:", chunk["file_path"])
            file_context += f"\n\n# From file: {chunk['file_path']}\n{chunk['text']}\n"

    prompt_type = Prompts.MAIN

    if tag:
        if tag == "primer":
            prompt_type = Prompts.UNIVERSAL_PRIMER
        elif tag == "concise":
            prompt_type = Prompts.CONCISE
        else:
            click.echo("Couldn't find the given prompt, using the default one.")

    console = Console()
    buffer = ""

    # Initialize Live context with empty Markdown
    with Live(
        Markdown(buffer), console=console, auto_refresh=True, screen=False
    ) as live:
        for token in llm.query_stream(prompt, file_context, prompt_type):
            buffer += token
            # Update the Live display with the new Markdown content
            live.update(Markdown(buffer))

    # Log the complete interaction
    response = str(buffer)
    logging.info({"query": prompt, "response": response})


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


@cli.command()
@click.option(
    "--provider",
    prompt="Provider (anthropic/deepseek)",
    help="LLM provider",
    default="anthropic",
)
@click.option(
    "--model",
    prompt="Default model",
    help="Default model to use",
    default="claude-3-5-sonnet-20241022",
)
@click.option("--api-key", prompt="API key", help="Provider API key")
def configure(provider, model, api_key):
    if provider not in PROVIDERS:
        click.echo(f"Error: Provider {provider} not supported")
        return

    config = load_config()
    setup_logging()
    config["provider"] = provider
    config["model"] = model

    env_var = f"{provider.upper()}_API_KEY"
    with open(os.path.expanduser("~/.bashrc"), "a") as f:
        f.write(f'\nexport {env_var}="{api_key}"\n')

    save_config(config)
    click.echo("Configuration saved")


@cli.command()
@click.option("--provider", help="LLM provider to use")
@click.option("--model", help="Model to use")
@click.option("-f", "--file", help="File to use as context")
@click.option(
    "-d", "--directory", help="Directory to use as context, use . for current dir"
)
@click.option("-c", "--codebase", help="Path to codebase to index and use as context")
def chat(provider, model, file, directory, codebase):
    """Start an interactive chat session with the LLM."""
    config = load_config()
    setup_logging()
    provider = provider or config["provider"]
    model = model or config.get("model")

    if provider not in PROVIDERS:
        click.echo(f"Error: Provider {provider} not supported")
        return

    provider_cls = PROVIDERS[provider]
    llm = provider_cls(model=model)
    prompt_type = Prompts.REPL
    console = Console()
    message_history = []

    file_context = ""

    if file:
        with open(file, "r") as f:
            file_context += f.read()

    if directory:
        file_context += read_directory(directory)

    if codebase:
        with console.status("[bold yellow]Indexing codebase, please wait...[/]"):
            # The name or path of the index file can be something like .cache/<hash_of_codebase>.pkl
            # so that if the codebase path is the same, we reuse the same index.
            # We'll just do a simple hash for uniqueness:
            codebase_hash = hashlib.md5(codebase.encode("utf-8")).hexdigest()
            index_path = os.path.join(".cache", f"codebase_index_{codebase_hash}.pkl")
            os.makedirs(".cache", exist_ok=True)

            # Build or load index
            index = build_codebase_index(codebase, index_path)

    console.print(
        "[bold blue]Chat session started. Type 'exit' to end the conversation.[/]"
    )

    files_provided = False
    while True:
        try:
            user_input = click.prompt("\n>>>", type=str)

            if user_input.lower() in ["exit", "quit"]:
                console.print("[bold blue]Ending chat session[/]")
                break

            if codebase:
                # Retrieve top chunks for the user's query
                relevant_chunks = retrieve_relevant_chunks(user_input, index, top_k=3)

                # Add them to the file_context
                for chunk in relevant_chunks:
                    print("Adding chunk from:", chunk["file_path"])
                    file_context += (
                        f"\n\n# From file: {chunk['file_path']}\n{chunk['text']}\n"
                    )

            response = ""
            with Live(
                Markdown(response), console=console, auto_refresh=True, screen=False
            ) as live:
                if files_provided:
                    for token in llm.query_stream(
                        prompt=user_input,
                        prompt_type=prompt_type,
                        message_history=message_history,
                    ):
                        response += token
                        live.update(Markdown(response))
                else:
                    for token in llm.query_stream(
                        prompt=user_input,
                        file_context=file_context,
                        prompt_type=prompt_type,
                        message_history=message_history,
                    ):
                        response += token
                        live.update(Markdown(response))
                    files_provided = True

            if response:
                logging.info({"query": user_input, "response": response})
                message_history.append(Message("user", user_input))
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


if __name__ == "__main__":
    cli()

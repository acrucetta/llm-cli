from datetime import datetime
import os
import click
import yaml
from pathlib import Path
import logging
import json
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from .providers import PROVIDERS
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "llm_cli" / "config.yml"
LOGS_PATH = Path.home() / ".config" / "llm_cli" / "logs"


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        return json.dumps(log_record)


def setup_logging():
    LOGS_PATH.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_PATH / f"llm_cli_{datetime.now().strftime('%Y%m')}.log"
    handler = logging.FileHandler(log_file)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def load_config():
    if not CONFIG_PATH.exists():
        return {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"}
    return yaml.safe_load(CONFIG_PATH.read_text())


def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(yaml.dump(config))


def extract_content_between_tags(content, start_tag, end_tag) -> str | None:
    start = content.find(start_tag)
    if start == -1:
        raise Exception("Start tag not found")
    start += len(start_tag)
    end = content.find(end_tag, start)
    if end == -1:
        raise Exception("End tag not found")
    return content[start:end].strip()


def read_directory(dir: str, context=None) -> str:
    if not context:
        context = ""
    try:
        dir_path = Path(dir)
        files = [f.name for f in dir_path.iterdir() if f.is_file()]
        dirs = [f.name for f in dir_path.iterdir() if f.is_dir()]

        # Read files
        for file_path in files:
            try:
                # Skip binary files and common non-text extensions
                file_extension = file_path.split(".")[-1]
                if file_extension in ["pyc", "pyo", "so", "dll", "bin"]:
                    continue
                with open(f"{dir}/{file_path}", "r", encoding="utf-8") as f:
                    context += f.read()
            except (UnicodeDecodeError, PermissionError, OSError) as e:
                click.echo(
                    f"Warning: Could not read {dir}/{file_path}: {str(e)}", err=True
                )
                continue
        for subdir in dirs:
            try:
                context = read_directory(subdir, context)
            except (PermissionError, OSError) as e:
                click.echo(
                    f"Warning: Could not access directory {subdir}: {str(e)}", err=True
                )
                continue
        return context
    except PermissionError as e:
        click.echo(f"Error: Permission denied accessing {dir_path}: {str(e)}", err=True)
        return context
    except OSError as e:
        click.echo(f"Error: Could not read directory {dir_path}: {str(e)}", err=True)
        return context


def format_response(text: str) -> list:
    lines = text.split("\n")
    in_code_block = False
    formatted_lines = []
    code_buffer = []
    language = ""

    for line in lines:
        if line.startswith("```"):
            if in_code_block:
                in_code_block = False
                code = "\n".join(code_buffer)
                syntax = Syntax(code, language or "text", theme="monokai")
                formatted_lines.append(syntax)
                code_buffer = []
            else:
                in_code_block = True
                language = line[3:].strip()
                continue
        elif in_code_block:
            code_buffer.append(line)
        else:
            formatted_lines.append(line)

    return formatted_lines


@click.group()
def cli():
    pass


@cli.command()
@click.argument("prompt")
@click.option("--provider", help="LLM provider to use")
@click.option("--model", help="Model to use")
@click.option("-f", "--file", help="File to use as context")
@click.option("-d", "--dir", help="Directory to use as context, use . for current dir")
def ask(prompt, provider, model, file, dir):
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

    if file:
        with open(file, "r") as f:
            file_context += f.read()

    if dir:
        file_context += read_directory(dir)

    response = llm.query(prompt, file_context)
    if response:
        # Log the interaction
        answer = extract_content_between_tags(response, "<answer>", "</answer>")
        logging.info("\nQuery:%s\nResponse:\n%s\n", prompt, answer)
        console = Console()
        formatted = format_response(answer)
        for content in formatted:
            if isinstance(content, str):
                console.print(Markdown(content))
            else:
                console.print(content)


@cli.command()
@click.option("-n", help="Show the last N logs")
def logs(n):
    curr_year, curr_month = datetime.now().year, datetime.now().month
    file_name = LOGS_PATH / f"llm_cli_{str(curr_year)}{curr_month:02}.log"
    with open(file_name, "r", encoding="utf-8") as f:
        log_entries = f.readlines()
        if n:
            log_entries = log_entries[-int(n) :]
        else:
            log_entries = log_entries[-10:]

        for log_entry in log_entries:
            log_dict = json.loads(log_entry)
            click.echo(
                f"{log_dict['timestamp']} - {log_dict['level']}: {log_dict['message']}"
            )


@cli.command()
@click.option("--provider", prompt="Provider (anthropic/openai)", help="LLM provider")
@click.option("--model", prompt="Default model", help="Default model to use")
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


if __name__ == "__main__":
    cli()

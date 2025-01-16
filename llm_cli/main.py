import os
import click
import yaml
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from .providers import PROVIDERS

CONFIG_PATH = Path.home() / ".config" / "llm_cli" / "config.yml"


def load_config():
    if not CONFIG_PATH.exists():
        return {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"}
    return yaml.safe_load(CONFIG_PATH.read_text())


def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(yaml.dump(config))


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
def ask(prompt, provider, model, file):
    config = load_config()
    provider = provider or config["provider"]
    model = model or config.get("model")

    if provider not in PROVIDERS:
        click.echo(f"Error: Provider {provider} not supported")
        return

    provider_cls = PROVIDERS[provider]
    llm = provider_cls(model=model)

    if file:
        with open(file, "r") as f:
            file_content = f.read()
            prompt += f"FILE CONTEXT:\n{file_content}"

    response = llm.query(prompt)
    if response:
        console = Console()
        formatted = format_response(response)
        for content in formatted:
            if isinstance(content, str):
                console.print(Markdown(content))
            else:
                console.print(content)


@cli.command()
@click.option("--provider", prompt="Provider (anthropic/openai)", help="LLM provider")
@click.option("--model", prompt="Default model", help="Default model to use")
@click.option("--api-key", prompt="API key", help="Provider API key")
def configure(provider, model, api_key):
    if provider not in PROVIDERS:
        click.echo(f"Error: Provider {provider} not supported")
        return

    config = load_config()
    config["provider"] = provider
    config["model"] = model

    env_var = f"{provider.upper()}_API_KEY"
    with open(os.path.expanduser("~/.bashrc"), "a") as f:
        f.write(f'\nexport {env_var}="{api_key}"\n')

    save_config(config)
    click.echo("Configuration saved")


if __name__ == "__main__":
    cli()

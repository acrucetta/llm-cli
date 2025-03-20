import json
import logging
from datetime import datetime
from pathlib import Path

import click
import yaml
from rich.syntax import Syntax


CONFIG_PATH = Path.home() / ".config" / "llm_cli" / "config.yml"
LOGS_PATH = Path.home() / ".config" / "llm_cli" / "logs"


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
        }
        if isinstance(record.msg, dict):
            # Merge dictionary messages into the log record
            log_record.update(record.msg)
        else:
            # Handle regular string messages
            log_record["message"] = record.getMessage()
        return json.dumps(log_record)


def setup_logging():
    LOGS_PATH.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_PATH / f"llm_cli_{datetime.now().strftime('%Y%m')}.log"
    handler = logging.FileHandler(log_file)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def load_config():
    default_config = {
        "provider": "anthropic",
        "provider_defaults": {
            "anthropic": "claude-3-7-sonnet-20250219",
            "gemini": "gemini-2.0-flash",
            "deepseek": "deepseek-chat",
            "openai": "o3-mini-2025-01-31",
        },
    }
    if not CONFIG_PATH.exists():
        return default_config
    config = yaml.safe_load(CONFIG_PATH.read_text())
    # Ensure defaults are present even if config file exists
    config.setdefault("provider", default_config["provider"])
    config.setdefault("provider_defaults", default_config["provider_defaults"])
    return config


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
                continue
        for subdir in dirs:
            try:
                context = read_directory(subdir, context)
            except (PermissionError, OSError) as e:
                continue
        return context
    except PermissionError as e:
        return context
    except OSError as e:
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


def format_prompt_with_context(prompt: str, file_context: str) -> str:
    """Format the prompt with file context and return the complete formatted prompt."""
    if not file_context:
        return prompt

    formatted_context = f"""
        <files_context>
        {file_context}
        </files_context>

        <user_query>
        {prompt}
        </user_query>
        """
    return formatted_context

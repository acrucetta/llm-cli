# Development Guidelines for LLM-CLI

## Build & Dev Commands
- Install dependencies: `poetry install`
- Run the CLI: `poetry run llm`
- Build package: `poetry build`
- Install locally: `pip install -e .`

## Code Style Guidelines
- **Imports**: Group by standard lib, third-party, local; alphabetize within groups
- **Formatting**: Follow PEP 8 conventions (4 spaces indentation)
- **Type Hints**: Use typing annotations for all function parameters and return values
- **Error Handling**: Use specific exceptions with descriptive messages; recover gracefully
- **Naming**:
  - snake_case for variables, functions, methods
  - CamelCase for classes
  - UPPER_CASE for constants

## Project Structure
- Keep provider implementations in `providers/` directory
- Utility functions in `utils/` directory
- Main CLI logic in `main.py`
- Follow single responsibility principle for modules

## API Access
- API keys should be stored as environment variables (ANTHROPIC_API_KEY, etc.)
- Never commit API keys to the repository
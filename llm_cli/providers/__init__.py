from .anthropic import AnthropicProvider
from .deepseek import DeepSeekProvider
from .gemini import GeminiProvider
from .openai import OpenAIProvider

PROVIDERS = {
    "anthropic": AnthropicProvider, 
    "deepseek": DeepSeekProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider
}

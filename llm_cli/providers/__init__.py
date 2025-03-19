from .anthropic import AnthropicProvider
from .deepseek import DeepSeekProvider
from .gemini import GeminiProvider

PROVIDERS = {
    "anthropic": AnthropicProvider, 
    "deepseek": DeepSeekProvider,
    "gemini": GeminiProvider
}

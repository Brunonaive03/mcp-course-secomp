from .env_setup import prepare_environment
from .llm_setup import (
    get_openai_client,
    get_openai_api_key,
    OpenAIAuthError,
    get_ollama_client,
    get_ollama_api_key,
    OllamaAuthError,
    get_llm_client,
)
from .chat_ui import launch_music_chat, build_music_chat_app
from .agent import MCPAgent

__all__ = [
    "prepare_environment",
    "get_openai_client",
    "get_openai_api_key",
    "OpenAIAuthError",
    "get_ollama_client",
    "get_ollama_api_key",
    "OllamaAuthError",
    "get_llm_client",
    "launch_music_chat",
    "build_music_chat_app",
    "MCPAgent",
]




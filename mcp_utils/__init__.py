import sys
from . import env
from . import llm
from . import agent
from . import chat

from .env.setup import prepare_environment
from .llm.setup import (
    get_openai_client,
    get_openai_api_key,
    OpenAIAuthError,
    get_ollama_client,
    get_ollama_api_key,
    OllamaAuthError,
    get_llm_client,
    get_api_key,
    LLMAuthError,
    DEFAULT_MODEL,
    DEFAULT_BASE_URL,
)
from .chat import launch_music_chat, build_music_chat_app, SPOTIFY_CSS
from .agent import MCPAgent

# Aliases de compatibilidade para suporte a maiúsculas e nomes legados
LLM = llm
ENV = env
Agent = agent
chat_ui = chat

sys.modules.setdefault("mcp_utils.LLM", llm)
sys.modules.setdefault("mcp_utils.LLM.setup", llm.setup)
sys.modules.setdefault("mcp_utils.ENV", env)
sys.modules.setdefault("mcp_utils.ENV.setup", env.setup)
sys.modules.setdefault("mcp_utils.chat_ui", chat)
sys.modules.setdefault("mcp_utils.Agent", agent)

__all__ = [
    "prepare_environment",
    "get_openai_client",
    "get_openai_api_key",
    "OpenAIAuthError",
    "get_ollama_client",
    "get_ollama_api_key",
    "OllamaAuthError",
    "get_llm_client",
    "get_api_key",
    "LLMAuthError",
    "DEFAULT_MODEL",
    "DEFAULT_BASE_URL",
    "launch_music_chat",
    "build_music_chat_app",
    "SPOTIFY_CSS",
    "MCPAgent",
    "llm",
    "env",
    "agent",
    "chat",
    "LLM",
    "ENV",
    "chat_ui",
]

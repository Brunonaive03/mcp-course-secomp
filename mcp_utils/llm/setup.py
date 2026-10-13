import os
import sys
from typing import Optional, Any


DEFAULT_MODEL = "gpt-oss:20b"
DEFAULT_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://ollama.com/v1")


class LLMAuthError(RuntimeError):
    """Exceção levantada quando a chave de API da LLM não é encontrada."""
    pass


# Aliases
OpenAIAuthError = LLMAuthError
OllamaAuthError = LLMAuthError


def get_api_key(api_key: Optional[str] = None, prompt_fallback: bool = False) -> str:
    """
    Obtém a chave de API buscando em:
    1. Parâmetro direto `api_key`.
    2. Variável de ambiente `OPENAI_API_KEY` ou `OLLAMA_API_KEY`.
    3. Google Colab Secrets (userdata.get('OPENAI_API_KEY') ou 'OLLAMA_API_KEY').
    4. Entrada interativa via getpass (se prompt_fallback=True).
    """
    if api_key and api_key.strip():
        return api_key.strip()

    # 1. Variáveis de ambiente
    for var in ["OPENAI_API_KEY", "OLLAMA_API_KEY"]:
        env_val = os.environ.get(var)
        if env_val and env_val.strip():
            return env_val.strip()

    # 2. Google Colab Secrets
    try:
        from google.colab import userdata  # type: ignore
        for var in ["OPENAI_API_KEY", "OLLAMA_API_KEY"]:
            try:
                colab_val = userdata.get(var)
                if colab_val and str(colab_val).strip():
                    return str(colab_val).strip()
            except Exception:
                pass
    except ImportError:
        pass
    except Exception:
        pass

    # 3. Fallback interativo (apenas se explicitamente habilitado)
    if prompt_fallback:
        try:
            import getpass
            print("\n🔑 Nenhuma chave encontrada no ambiente ou Colab Secrets.")
            user_input = getpass.getpass("Digite sua chave de API (OPENAI_API_KEY ou OLLAMA_API_KEY): ")
            if user_input and user_input.strip():
                os.environ["OPENAI_API_KEY"] = user_input.strip()
                return user_input.strip()
        except Exception:
            pass

    msg = (
        "\n" + "=" * 70 + "\n"
        "🔑 CHAVE DE API NÃO ENCONTRADA!\n"
        "=" * 70 + "\n"
        "Para utilizar o modelo gpt-oss:20b no curso:\n\n"
        "1. No Google Colab:\n"
        "   - Clique no ícone de Chave/Segredos (🔑) no painel lateral esquerdo.\n"
        "   - Adicione um segredo com o nome: OPENAI_API_KEY (ou OLLAMA_API_KEY)\n"
        "   - Ative a opção 'Acesso ao notebook' (Notebook access).\n\n"
        "Alternativamente, defina no Python:\n"
        "   import os\n"
        "   os.environ['OPENAI_API_KEY'] = 'sua_chave'\n"
        "=" * 70 + "\n"
    )
    print(msg, file=sys.stderr)
    raise LLMAuthError("Chave de API ausente. Siga as instruções acima para configurá-la.")


def get_openai_api_key(api_key: Optional[str] = None, prompt_fallback: bool = False) -> str:
    return get_api_key(api_key=api_key, prompt_fallback=prompt_fallback)


def get_ollama_api_key(api_key: Optional[str] = None, prompt_fallback: bool = False) -> str:
    return get_api_key(api_key=api_key, prompt_fallback=prompt_fallback)


def get_openai_client(
    api_key: Optional[str] = None,
    default_model: str = DEFAULT_MODEL,
    base_url: Optional[str] = None,
    prompt_fallback: bool = False,
    **client_kwargs
) -> Any:
    """
    Inicializa o cliente OpenAI configurado internamente para o modelo gpt-oss:20b.

    Parâmetros:
    - `api_key`: Chave de API opcional.
    - `default_model`: Modelo padrão (padrão interno: 'gpt-oss:20b').
    - `base_url`: Endpoint da API (padrão: 'https://ollama.com/v1').
    """
    key = get_api_key(api_key=api_key, prompt_fallback=prompt_fallback)


    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "A biblioteca 'openai' não está instalada. Instale com: pip install openai"
        )

    url = base_url or DEFAULT_BASE_URL
    kwargs = {"api_key": key, "base_url": url, **client_kwargs}

    client = OpenAI(**kwargs)
    client.default_model = default_model  # type: ignore
    return client


# Aliases para conveniência
get_ollama_client = get_openai_client
get_llm_client = get_openai_client

import os
import sys
from typing import Optional, Any


DEFAULT_MODEL = "gpt-oss:20b"
DEFAULT_OLLAMA_BASE_URL = "https://ollama.com/v1"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"

# Mantido para retrocompatibilidade com imports diretos
DEFAULT_BASE_URL = DEFAULT_OLLAMA_BASE_URL


class LLMAuthError(RuntimeError):
    """Exceção levantada quando a chave de API da LLM não é encontrada ou está incorreta."""
    pass


# Aliases
OpenAIAuthError = LLMAuthError
OllamaAuthError = LLMAuthError


def get_api_key(
    api_key: Optional[str] = None,
    preferred_env: str = "OLLAMA_API_KEY",
    prompt_fallback: bool = False
) -> str:
    """
    Obtém a chave de API buscando em:
    1. Parâmetro direto `api_key`.
    2. Variável de ambiente preferida e alternativas (`OLLAMA_API_KEY`, `OPENAI_API_KEY`).
    3. Google Colab Secrets (userdata.get).
    4. Entrada interativa via getpass (se prompt_fallback=True).
    """
    if api_key and api_key.strip():
        return api_key.strip()

    search_order = (
        [preferred_env, "OLLAMA_API_KEY", "OPENAI_API_KEY"]
        if preferred_env != "OLLAMA_API_KEY"
        else ["OLLAMA_API_KEY", "OPENAI_API_KEY"]
    )
    # Deduplica mantendo a ordem
    seen = set()
    env_vars = [v for v in search_order if not (v in seen or seen.add(v))]

    # 1. Variáveis de ambiente
    for var in env_vars:
        env_val = os.environ.get(var)
        if env_val and env_val.strip():
            return env_val.strip()

    # 2. Google Colab Secrets
    try:
        from google.colab import userdata  # type: ignore
        for var in env_vars:
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
            print(f"\n🔑 Nenhuma chave encontrada no ambiente ou Colab Secrets.")
            user_input = getpass.getpass(f"Digite sua chave de API ({preferred_env}): ")
            if user_input and user_input.strip():
                os.environ[preferred_env] = user_input.strip()
                return user_input.strip()
        except Exception:
            pass

    msg = (
        "\n" + "=" * 70 + "\n"
        "🔑 CHAVE DE API NÃO ENCONTRADA!\n"
        "=" * 70 + "\n"
        f"Para utilizar o modelo {DEFAULT_MODEL} no minicurso:\n\n"
        "1. No Google Colab:\n"
        "   - Clique no ícone de Chave/Segredos (🔑) no painel lateral esquerdo.\n"
        "   - Adicione um segredo com o nome: OLLAMA_API_KEY (ou OPENAI_API_KEY)\n"
        "   - Ative a opção 'Acesso ao notebook' (Notebook access).\n\n"
        "Alternativamente, defina no Python:\n"
        "   import os\n"
        "   os.environ['OLLAMA_API_KEY'] = 'sua_chave'\n"
        "=" * 70 + "\n"
    )
    print(msg, file=sys.stderr)
    raise LLMAuthError("Chave de API ausente. Siga as instruções acima para configurá-la.")


def get_ollama_client(
    api_key: Optional[str] = None,
    default_model: str = DEFAULT_MODEL,
    base_url: Optional[str] = None,
    prompt_fallback: bool = False,
    **client_kwargs
) -> Any:
    """
    Inicializa o cliente para o Ollama Cloud (padrão do minicurso com gpt-oss:20b).
    """
    url = (
        base_url
        or os.environ.get("OLLAMA_BASE_URL")
        or DEFAULT_OLLAMA_BASE_URL
    )
    key = get_api_key(
        api_key=api_key,
        preferred_env="OLLAMA_API_KEY",
        prompt_fallback=prompt_fallback
    )

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "A biblioteca 'openai' não está instalada. Instale com: pip install openai"
        )

    client = OpenAI(api_key=key, base_url=url, **client_kwargs)
    client.default_model = default_model  # type: ignore
    return client


def get_openai_client(
    api_key: Optional[str] = None,
    default_model: Optional[str] = None,
    base_url: Optional[str] = None,
    prompt_fallback: bool = False,
    **client_kwargs
) -> Any:
    """
    Inicializa cliente LLM. Se base_url for omitida:
    - Se OLLAMA_API_KEY estiver configurada, conecta à Ollama Cloud (gpt-oss:20b).
    - Se OPENAI_BASE_URL estiver configurada, conecta a esse endpoint customizado.
    - Se apenas OPENAI_API_KEY estiver presente e a chave começar com 'sk-', conecta à API da OpenAI oficial
      para evitar envio indevido da chave OpenAI a servidores de terceiros.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "A biblioteca 'openai' não está instalada. Instale com: pip install openai"
        )

    # 1. Se base_url foi passada explicitamente, respeita a escolha
    if base_url:
        key = get_api_key(api_key=api_key, prompt_fallback=prompt_fallback)
        model = default_model or DEFAULT_MODEL
        client = OpenAI(api_key=key, base_url=base_url, **client_kwargs)
        client.default_model = model  # type: ignore
        return client

    # 2. Resolução dinâmica de endpoint e chave
    has_ollama_key = bool(os.environ.get("OLLAMA_API_KEY"))
    has_openai_key = bool(os.environ.get("OPENAI_API_KEY"))
    custom_base = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OLLAMA_BASE_URL")

    if custom_base:
        key = get_api_key(api_key=api_key, preferred_env="OPENAI_API_KEY" if has_openai_key else "OLLAMA_API_KEY", prompt_fallback=prompt_fallback)
        model = default_model or DEFAULT_MODEL
        client = OpenAI(api_key=key, base_url=custom_base, **client_kwargs)
        client.default_model = model  # type: ignore
        return client

    if has_ollama_key or not has_openai_key:
        # Padrão do laboratório: Ollama Cloud
        return get_ollama_client(
            api_key=api_key,
            default_model=default_model or DEFAULT_MODEL,
            prompt_fallback=prompt_fallback,
            **client_kwargs
        )

    # Caso onde apenas OPENAI_API_KEY está definida e nenhum custom_base foi definido:
    key = get_api_key(api_key=api_key, preferred_env="OPENAI_API_KEY", prompt_fallback=prompt_fallback)
    if key.startswith("sk-") and not default_model:
        # Usuário configurou chave da OpenAI oficial: conectar à OpenAI oficial para não vazar a chave
        url = DEFAULT_OPENAI_BASE_URL
        model = "gpt-4o-mini"
        print(f"ℹ️ [LLM Setup] Usando endpoint oficial da OpenAI ({url}) com modelo '{model}'.", flush=True)
    else:
        url = DEFAULT_OLLAMA_BASE_URL
        model = default_model or DEFAULT_MODEL

    client = OpenAI(api_key=key, base_url=url, **client_kwargs)
    client.default_model = model  # type: ignore
    return client


# Aliases
get_llm_client = get_openai_client
get_openai_api_key = lambda **kw: get_api_key(preferred_env="OPENAI_API_KEY", **kw)
get_ollama_api_key = lambda **kw: get_api_key(preferred_env="OLLAMA_API_KEY", **kw)

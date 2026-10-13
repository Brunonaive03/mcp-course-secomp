import inspect
from typing import Any, Callable, Optional

import gradio as gr

from .styles import SPOTIFY_CSS
from .builder import build_music_chat_app


def launch_music_chat(
    chat_fn: Optional[Callable[[str, list], Any]] = None,
    server: Optional[Any] = None,
    model: str = "gpt-oss:20b",
    title: str = "🎵 MCP Music Assistant",
    subtitle: str = "Mini-curso MCP - SECOMP UFPE",
    share: bool = True,
    inline: bool = False,
    block: bool = True,
    server_port: int = 7860,
    **launch_kwargs
) -> Any:
    """
    Inicia o servidor Gradio com a interface de chat e player de música estilo Spotify.

    - `inline=False`: Desativa o iframe na saída da célula do Colab, forçando a abertura via link externo.
    - `share=True`: Gera uma URL pública compartilhável (gradio.live).
    - `block=True`: Mantém a célula em execução enquanto o chat estiver aberto (ao interromper a célula, fecha o servidor).
    """
    app = build_music_chat_app(
        chat_fn=chat_fn,
        server=server,
        model=model,
        title=title,
        subtitle=subtitle
    )

    launch_params = inspect.signature(app.launch).parameters
    if "css" in launch_params and "css" not in launch_kwargs:
        launch_kwargs["css"] = SPOTIFY_CSS
    if "theme" in launch_params and "theme" not in launch_kwargs:
        launch_kwargs["theme"] = gr.themes.Base()

    # Inicia com inline desativado para abrir em nova aba
    launch_result = app.launch(
        share=share,
        inline=inline,
        server_port=server_port,
        prevent_thread_lock=not block,
        **launch_kwargs
    )

    target_url = getattr(app, "share_url", None) or getattr(app, "local_url", None) or f"http://localhost:{server_port}"

    print("\n" + "=" * 65)
    print("🎵 MCP Music Chat iniciado com sucesso!")
    print(f"👉 Abra o chat no seu navegador: {target_url}")
    if share:
        print("⚠️ [Segurança] share=True gera um link público no gradio.live.")
        print("   Qualquer pessoa com esse link poderá enviar mensagens consumindo a cota da sua chave de API.")
    print("⏹️ Para encerrar o chat, clique no botão Interromper (Stop ⏹️) da célula.")
    print("=" * 65 + "\n")

    if block:
        try:
            app.block_thread()
        except (KeyboardInterrupt, Exception):
            print("\n⏹️ Chat encerrado com sucesso.")
            app.close()

    return launch_result

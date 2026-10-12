import html
import inspect
from typing import Any, Callable, Dict, Optional, Tuple, Union
import gradio as gr


SPOTIFY_CSS = """
/* Spotify Dark Theme Styles */
body, .gradio-container {
    background-color: #121212 !important;
    color: #FFFFFF !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}

#music-chatbot {
    background-color: #181818 !important;
    border: 1px solid #282828 !important;
    border-radius: 12px !important;
}

#spotify-player-bar {
    background: linear-gradient(180deg, #181818 0%, #121212 100%) !important;
    border: 1px solid #282828 !important;
    border-radius: 16px !important;
    padding: 16px 20px !important;
    margin-top: 16px !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7) !important;
}

.spotify-track-container {
    display: flex;
    align-items: center;
    gap: 16px;
}

.spotify-cover-art {
    width: 68px;
    height: 68px;
    border-radius: 8px;
    object-fit: cover;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6);
    background-color: #282828;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    flex-shrink: 0;
}

.spotify-track-meta {
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: hidden;
}

.spotify-badge {
    color: #1DB954;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 2px;
}

.spotify-track-title {
    color: #FFFFFF;
    font-size: 15px;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin: 0;
}

.spotify-track-artist {
    color: #B3B3B3;
    font-size: 13px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin: 2px 0 0 0;
}

.spotify-empty-state {
    color: #727272;
    font-size: 13px;
    font-style: italic;
    margin: 2px 0 0 0;
}

#spotify-audio-player {
    background: transparent !important;
    border: none !important;
}

.spotify-send-btn {
    background-color: #1DB954 !important;
    color: #000000 !important;
    font-weight: 700 !important;
    border-radius: 50px !important;
    border: none !important;
    transition: transform 0.2s, background-color 0.2s !important;
}

.spotify-send-btn:hover {
    background-color: #1ed760 !important;
    transform: scale(1.02) !important;
}
"""


def _normalize_track(track_data: Any) -> Optional[Dict[str, Any]]:
    """Normaliza os dados da faixa recebidos do agente ou do recurso MCP."""
    if not track_data:
        return None

    # Se for uma string representando um ID de faixa (ex: 'trk_1dcdf5eadf')
    if isinstance(track_data, str) and track_data.strip().startswith("trk_"):
        track_id = track_data.strip()
        return {"title": track_id, "artists": ["Faixa MCP"], "resources": {}}

    # Se for um dicionário de metadados
    if isinstance(track_data, dict):
        return track_data

    return None



def _format_track_html(track: Optional[Dict[str, Any]]) -> str:
    """Gera o HTML do card de faixa do player estilo Spotify."""
    if not track:
        return """
        <div class="spotify-track-container">
            <div class="spotify-cover-art">🎵</div>
            <div class="spotify-track-meta">
                <span class="spotify-badge" style="color: #727272;">Player em espera</span>
                <p class="spotify-track-title" style="color: #B3B3B3;">Nenhuma faixa selecionada</p>
                <p class="spotify-empty-state">Peça uma música ao assistente no chat acima!</p>
            </div>
        </div>
        """

    title = html.escape(str(track.get("title", "Faixa sem título")))
    artists = track.get("artists") or [track.get("artist", "Artista desconhecido")]
    if isinstance(artists, list):
        artist_str = ", ".join(str(a) for a in artists)
    else:
        artist_str = str(artists)
    artist_str = html.escape(artist_str)

    resources = track.get("resources") or {}
    thumb_url = resources.get("thumbnail_url") or track.get("thumbnail_url") or ""

    if thumb_url:
        cover_html = f'<img src="{html.escape(thumb_url)}" class="spotify-cover-art" alt="Capa">'
    else:
        cover_html = '<div class="spotify-cover-art">🎧</div>'

    return f"""
    <div class="spotify-track-container">
        {cover_html}
        <div class="spotify-track-meta">
            <span class="spotify-badge">▶ Tocando agora</span>
            <p class="spotify-track-title" title="{title}">{title}</p>
            <p class="spotify-track-artist" title="{artist_str}">{artist_str}</p>
        </div>
    </div>
    """


def _extract_preview_url(track: Optional[Dict[str, Any]]) -> Optional[str]:
    """Extrai a URL do preview em áudio."""
    if not track:
        return None
    resources = track.get("resources") or {}
    return resources.get("preview_url") or track.get("preview_url")


def build_music_chat_app(
    chat_fn: Optional[Callable[[str, list], Any]] = None,
    server: Optional[Any] = None,
    model: str = "gpt-oss:20b",
    title: str = "🎵 MCP Music Assistant",
    subtitle: str = "Mini-curso MCP - SECOMP UFPE"
) -> gr.Blocks:
    """
    Constrói a interface Gradio Blocks com Chatbot e Player Spotify integrado.

    - Se `chat_fn` não for fornecido e `server` for passado: inicializa o `MCPAgent` internamente.
    - Se `chat_fn` e `server` forem None: conecta internamente ao `gpt-oss:20b`.
    - Se `chat_fn` for fornecido: utiliza a função de chat customizada.
    """
    if chat_fn is None:
        if server is not None:
            from .agent import MCPAgent
            try:
                agent = MCPAgent(server=server, model=model)
                actual_chat_fn = agent.chat
            except Exception as e:
                def agent_init_err(user_msg: str, history: list):
                    return f"⚠️ Não foi possível iniciar o agente: {e}"
                actual_chat_fn = agent_init_err
        else:
            from .llm_setup import get_openai_client

            try:
                client = get_openai_client(default_model=model)
                client_err = None
            except Exception as e:
                client = None
                client_err = str(e)

            def internal_llm_chat(user_msg: str, history: list):
                if client is None:
                    yield f"⚠️ Chave de API não configurada ({client_err}). Configure OPENAI_API_KEY ou OLLAMA_API_KEY nos Secrets do Colab."
                    return

                messages = [{"role": "system", "content": "Você é um assistente de música amigável."}]
                for turn in (history or []):
                    messages.append({"role": turn["role"], "content": turn["content"]})
                messages.append({"role": "user", "content": user_msg})

                try:
                    response_stream = client.chat.completions.create(
                        model=getattr(client, "default_model", model),
                        messages=messages,
                        stream=True
                    )
                    accumulated = ""
                    for chunk in response_stream:
                        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                            accumulated += chunk.choices[0].delta.content
                            yield accumulated
                except Exception as err:
                    yield f"⚠️ Erro ao consultar modelo {model}: {err}"

            actual_chat_fn = internal_llm_chat
    else:
        actual_chat_fn = chat_fn

    blocks_kwargs: Dict[str, Any] = {"title": title}
    blocks_init_params = inspect.signature(gr.Blocks.__init__).parameters
    if "theme" in blocks_init_params:
        blocks_kwargs["theme"] = gr.themes.Base()
    if "css" in blocks_init_params:
        blocks_kwargs["css"] = SPOTIFY_CSS

    with gr.Blocks(**blocks_kwargs) as demo:
        # Injeção de CSS para garantir renderização idêntica em qualquer versão do Gradio
        gr.HTML(f"<style>{SPOTIFY_CSS}</style>")

        # Cabeçalho
        with gr.Row():
            with gr.Column():
                gr.Markdown(f"# {title}\n### {subtitle}")

        # Janela do Chat
        chatbot = gr.Chatbot(
            elem_id="music-chatbot",
            height=460,
        )

        # Entrada de Texto
        with gr.Row():
            msg_input = gr.Textbox(
                placeholder="Ex: Recomende uma música do Oasis e toque para mim...",
                show_label=False,
                scale=8,
                container=False,
            )
            send_btn = gr.Button("Enviar", variant="primary", scale=1, elem_classes=["spotify-send-btn"])
            clear_btn = gr.ClearButton(components=[msg_input, chatbot], value="Limpar", scale=1)

        # Barra do Player Spotify (Dock Inferior)
        with gr.Group(elem_id="spotify-player-bar"):
            with gr.Row(elem_classes=["spotify-player-row"]):
                with gr.Column(scale=4, min_width=280):
                    track_display = gr.HTML(value=_format_track_html(None))
                with gr.Column(scale=5, min_width=320):
                    audio_player = gr.Audio(
                        value=None,
                        autoplay=True,
                        show_label=False,
                        elem_id="spotify-audio-player",
                        type="filepath",
                    )

        # Estado atual da faixa tocando
        current_track_state = gr.State(value=None)

        def process_turn(user_msg: str, history: list, current_track: Any):
            if not user_msg or not user_msg.strip():
                yield "", history, _format_track_html(current_track), _extract_preview_url(current_track), current_track
                return

            print(f"\n🎧 [Chat UI] Processando mensagem do usuário: \"{user_msg}\"", flush=True)
            history = history or []
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": "..."})
            yield "", history, _format_track_html(current_track), _extract_preview_url(current_track), current_track

            try:
                result = actual_chat_fn(user_msg, history[:-2])
            except Exception as e:
                import traceback
                print(f"❌ [Chat UI Error] Exceção ao executar o chat: {e}", flush=True)
                traceback.print_exc()
                history[-1]["content"] = f"⚠️ Erro ao processar mensagem com o agente: {e}"
                yield "", history, _format_track_html(current_track), _extract_preview_url(current_track), current_track
                return

            new_track = current_track

            # Se for um generator/iterator (streaming token a token)
            if inspect.isgenerator(result) or inspect.isgeneratorfunction(actual_chat_fn):
                for chunk in result:
                    if isinstance(chunk, (tuple, list)) and len(chunk) >= 2:
                        reply_part = str(chunk[0])
                        candidate_track = _normalize_track(chunk[1])
                        if candidate_track:
                            new_track = candidate_track
                    else:
                        reply_part = str(chunk)

                    history[-1]["content"] = reply_part
                    yield "", history, _format_track_html(new_track), _extract_preview_url(new_track), new_track
            else:
                if isinstance(result, (tuple, list)) and len(result) >= 2:
                    reply_text = str(result[0] or "")
                    candidate_track = _normalize_track(result[1])
                    if candidate_track:
                        new_track = candidate_track
                elif isinstance(result, dict) and "reply" in result:
                    reply_text = str(result.get("reply", "") or "")
                    candidate_track = _normalize_track(result.get("track"))
                    if candidate_track:
                        new_track = candidate_track
                else:
                    reply_text = str(result or "")

                if not reply_text.strip():
                    if new_track and isinstance(new_track, dict) and new_track.get("title"):
                        reply_text = f"Faixa **{new_track.get('title')}** carregada no player."
                    else:
                        reply_text = "Processado com sucesso."

                if new_track:
                    track_name = new_track.get("title") if isinstance(new_track, dict) else new_track
                    print(f"▶️ [Chat UI] Faixa sincronizada com o player: {track_name}", flush=True)

                print(f"🎧 [Chat UI] Exibindo resposta no chat ({len(reply_text)} caracteres)...", flush=True)

                # Efeito visual de digitação
                import time
                words = reply_text.split(" ")
                accumulated = ""
                for i, word in enumerate(words):
                    accumulated += (word if i == 0 else " " + word)
                    history[-1]["content"] = accumulated
                    yield "", history, _format_track_html(new_track), _extract_preview_url(new_track), new_track
                    time.sleep(0.015)

            print(f"✅ [Chat UI] Turno finalizado com sucesso.\n", flush=True)


        # Ações de envio
        msg_input.submit(
            fn=process_turn,
            inputs=[msg_input, chatbot, current_track_state],
            outputs=[msg_input, chatbot, track_display, audio_player, current_track_state]
        )
        send_btn.click(
            fn=process_turn,
            inputs=[msg_input, chatbot, current_track_state],
            outputs=[msg_input, chatbot, track_display, audio_player, current_track_state]
        )

    return demo


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
    print("⏹️ Para encerrar o chat, clique no botão Interromper (Stop ⏹️) da célula.")
    print("=" * 65 + "\n")

    if block:
        try:
            app.block_thread()
        except (KeyboardInterrupt, Exception):
            print("\n⏹️ Chat encerrado com sucesso.")
            app.close()

    return launch_result



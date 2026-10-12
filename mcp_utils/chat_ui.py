import html
import inspect
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
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

.spotify-badge-preview {
    background: rgba(29, 185, 84, 0.15);
    color: #1DB954;
    border: 1px solid rgba(29, 185, 84, 0.5);
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.5px;
    display: inline-block;
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

.spotify-preview-note {
    color: #888888;
    font-size: 11px;
    margin: 3px 0 0 0;
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

.spotify-nav-btn {
    background-color: #282828 !important;
    color: #FFFFFF !important;
    border: 1px solid #3e3e3e !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    padding: 6px 12px !important;
    transition: background-color 0.2s, border-color 0.2s !important;
}

.spotify-nav-btn:hover {
    background-color: #383838 !important;
    border-color: #1DB954 !important;
    color: #1DB954 !important;
}
"""


def _normalize_track(track_data: Any) -> Optional[Dict[str, Any]]:
    """Normaliza um único registro de faixa recebido do agente ou do recurso MCP."""
    if not track_data:
        return None

    if isinstance(track_data, str) and track_data.strip().startswith("trk_"):
        track_id = track_data.strip()
        return {"title": track_id, "artists": ["Faixa MCP"], "resources": {}, "track_id": track_id}

    if isinstance(track_data, dict):
        return track_data

    return None


def _normalize_tracks(candidate: Any) -> List[Dict[str, Any]]:
    """Normaliza faixas recebidas (única ou lista) para uma lista de dicionários."""
    if not candidate:
        return []

    tracks: List[Dict[str, Any]] = []
    if isinstance(candidate, (list, tuple)):
        for item in candidate:
            norm = _normalize_track(item)
            if norm:
                tracks.append(norm)
    else:
        norm = _normalize_track(candidate)
        if norm:
            tracks.append(norm)

    return tracks


def _build_dropdown_choices(playlist: List[Dict[str, Any]]) -> List[str]:
    """Gera lista de rótulos formatados para o dropdown da playlist."""
    choices = []
    for i, t in enumerate(playlist):
        title = t.get("title", f"Faixa {i+1}")
        artists = t.get("artists") or [t.get("artist", "")]
        art_str = f" - {', '.join(str(a) for a in artists if a)}" if artists else ""
        choices.append(f"{i+1}. {title}{art_str}")
    return choices


def _get_index_from_selection(selection: Optional[str], choices: List[str]) -> int:
    """Recupera o índice 0-based da faixa selecionada no dropdown."""
    if not selection:
        return 0
    if selection in choices:
        return choices.index(selection)
    try:
        parts = selection.split(".", 1)
        return max(0, int(parts[0].strip()) - 1)
    except Exception:
        return 0


def _format_track_html(track: Optional[Dict[str, Any]], current_idx: int = 0, total_tracks: int = 0) -> str:
    """Gera o HTML do card de faixa do player estilo Spotify com indicação explícita de prévia."""
    if not track:
        return """
        <div class="spotify-track-container">
            <div class="spotify-cover-art">🎵</div>
            <div class="spotify-track-meta">
                <span class="spotify-badge" style="color: #727272;">Player em espera</span>
                <p class="spotify-track-title" style="color: #B3B3B3;">Nenhuma faixa selecionada</p>
                <p class="spotify-empty-state">Peça músicas de um artista no chat para ouvir as prévias!</p>
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

    counter_badge = ""
    if total_tracks > 1:
        counter_badge = f'<span style="background: #282828; color: #1DB954; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;">Faixa {current_idx + 1} de {total_tracks}</span>'

    return f"""
    <div class="spotify-track-container">
        {cover_html}
        <div class="spotify-track-meta">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span class="spotify-badge-preview">▶️ PRÉVIA DA MÚSICA (30s)</span>
                {counter_badge}
            </div>
            <p class="spotify-track-title" title="{title}">{title}</p>
            <p class="spotify-track-artist" title="{artist_str}">{artist_str}</p>
            <p class="spotify-preview-note">⏱️ Amostra de áudio de 30s resolvida via MCP Resource</p>
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

        # Banner de Ferramentas e Recursos MCP conectados (se server foi passado)
        tools_list = []
        resources_list = []
        if server is not None:
            if hasattr(server, "_tool_manager") and hasattr(server._tool_manager, "_tools"):
                for name, t in server._tool_manager._tools.items():
                    desc = getattr(t, "description", "") or ""
                    desc_str = f" ({desc.strip()})" if desc else ""
                    tools_list.append(f"<code>{html.escape(name)}</code>{html.escape(desc_str)}")
            if hasattr(server, "_resource_manager") and hasattr(server._resource_manager, "_templates"):
                for uri_tpl in server._resource_manager._templates.keys():
                    resources_list.append(f"<code>{html.escape(uri_tpl)}</code>")

        if tools_list or resources_list:
            banner_html = "<div style='background: #181818; border: 1px solid #282828; border-radius: 10px; padding: 12px 18px; margin-bottom: 12px; font-size: 13px;'>"
            if tools_list:
                banner_html += f"<div style='margin-bottom: 4px;'><strong style='color: #1DB954;'>🛠️ Ferramentas MCP Ativas ({len(tools_list)}):</strong> " + " • ".join(tools_list) + "</div>"
            if resources_list:
                banner_html += f"<div><strong style='color: #3b82f6;'>📖 Recursos MCP:</strong> " + " • ".join(resources_list) + "</div>"
            banner_html += "</div>"
            gr.HTML(banner_html)

        # Janela do Chat
        chatbot = gr.Chatbot(
            elem_id="music-chatbot",
            height=460,
        )

        # Entrada de Texto
        with gr.Row():
            msg_input = gr.Textbox(
                placeholder="Ex: Recomende músicas do Oasis e toque para mim...",
                show_label=False,
                scale=8,
                container=False,
            )
            send_btn = gr.Button("Enviar", variant="primary", scale=1, elem_classes=["spotify-send-btn"])
            clear_btn = gr.ClearButton(components=[msg_input, chatbot], value="Limpar", scale=1)

        # Barra do Player Spotify (Dock Inferior com Playlist de Prévias)
        with gr.Group(elem_id="spotify-player-bar"):
            with gr.Row():
                gr.Markdown("#### 🎧 Player de Prévias Musicais (30s)")
            with gr.Row(elem_classes=["spotify-player-row"]):
                # Coluna 1: Card da Faixa (Capa, Título, Artista, Badge de Prévia 30s)
                with gr.Column(scale=5, min_width=270):
                    track_display = gr.HTML(value=_format_track_html(None))
                # Coluna 2: Seletor de Playlist e Alternância entre Prévias
                with gr.Column(scale=4, min_width=250):
                    track_dropdown = gr.Dropdown(
                        label="🎵 Alternar Prévia (Playlist)",
                        choices=[],
                        value=None,
                        interactive=True,
                    )
                    with gr.Row():
                        prev_btn = gr.Button("⏮️ Anterior", size="sm", elem_classes=["spotify-nav-btn"])
                        next_btn = gr.Button("Próxima ⏭️", size="sm", elem_classes=["spotify-nav-btn"])
                # Coluna 3: Player de Áudio Gradio
                with gr.Column(scale=4, min_width=260):
                    audio_player = gr.Audio(
                        value=None,
                        autoplay=True,
                        show_label=True,
                        label="▶️ Tocando Prévia (30s)",
                        elem_id="spotify-audio-player",
                        type="filepath",
                    )

        # Estado da playlist e do índice atual
        playlist_state = gr.State(value=[])
        current_index_state = gr.State(value=0)

        def switch_track_prev(playlist: list, current_idx: int):
            playlist = playlist or []
            if not playlist:
                return _format_track_html(None), None, 0, gr.update(choices=[], value=None)
            new_idx = (current_idx - 1) % len(playlist)
            track = playlist[new_idx]
            choices = _build_dropdown_choices(playlist)
            sel_val = choices[new_idx] if new_idx < len(choices) else None
            return (
                _format_track_html(track, new_idx, len(playlist)),
                _extract_preview_url(track),
                new_idx,
                gr.update(value=sel_val),
            )

        def switch_track_next(playlist: list, current_idx: int):
            playlist = playlist or []
            if not playlist:
                return _format_track_html(None), None, 0, gr.update(choices=[], value=None)
            new_idx = (current_idx + 1) % len(playlist)
            track = playlist[new_idx]
            choices = _build_dropdown_choices(playlist)
            sel_val = choices[new_idx] if new_idx < len(choices) else None
            return (
                _format_track_html(track, new_idx, len(playlist)),
                _extract_preview_url(track),
                new_idx,
                gr.update(value=sel_val),
            )

        def on_track_select(selection: Optional[str], playlist: list):
            playlist = playlist or []
            if not playlist or not selection:
                return _format_track_html(None), None, 0
            choices = _build_dropdown_choices(playlist)
            new_idx = _get_index_from_selection(selection, choices)
            if new_idx < 0 or new_idx >= len(playlist):
                new_idx = 0
            track = playlist[new_idx]
            return (
                _format_track_html(track, new_idx, len(playlist)),
                _extract_preview_url(track),
                new_idx,
            )

        def process_turn(user_msg: str, history: list, playlist: list, current_idx: int):
            playlist = playlist or []
            curr_track = playlist[current_idx] if (playlist and 0 <= current_idx < len(playlist)) else None
            choices = _build_dropdown_choices(playlist)
            sel_val = choices[current_idx] if (choices and 0 <= current_idx < len(choices)) else None

            if not user_msg or not user_msg.strip():
                yield "", history, _format_track_html(curr_track, current_idx, len(playlist)), _extract_preview_url(curr_track), playlist, current_idx, gr.update(choices=choices, value=sel_val)
                return

            print(f"\n🎧 [Chat UI] Processando mensagem do usuário: \"{user_msg}\"", flush=True)
            history = history or []
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": "..."})
            yield "", history, _format_track_html(curr_track, current_idx, len(playlist)), _extract_preview_url(curr_track), playlist, current_idx, gr.update(choices=choices, value=sel_val)

            try:
                result = actual_chat_fn(user_msg, history[:-2])
            except Exception as e:
                import traceback
                print(f"❌ [Chat UI Error] Exceção ao executar o chat: {e}", flush=True)
                traceback.print_exc()
                history[-1]["content"] = f"⚠️ Erro ao processar mensagem com o agente: {e}"
                yield "", history, _format_track_html(curr_track, current_idx, len(playlist)), _extract_preview_url(curr_track), playlist, current_idx, gr.update(choices=choices, value=sel_val)
                return

            new_playlist = playlist
            new_idx = current_idx

            # Se for um generator/iterator (streaming token a token)
            if inspect.isgenerator(result) or inspect.isgeneratorfunction(actual_chat_fn):
                for chunk in result:
                    if isinstance(chunk, (tuple, list)) and len(chunk) >= 2:
                        reply_part = str(chunk[0])
                        candidate_tracks = _normalize_tracks(chunk[1])
                        if candidate_tracks:
                            new_playlist = candidate_tracks
                            new_idx = 0
                    else:
                        reply_part = str(chunk)

                    history[-1]["content"] = reply_part
                    curr_t = new_playlist[new_idx] if (new_playlist and 0 <= new_idx < len(new_playlist)) else None
                    new_choices = _build_dropdown_choices(new_playlist)
                    new_sel = new_choices[new_idx] if (new_choices and 0 <= new_idx < len(new_choices)) else None
                    yield "", history, _format_track_html(curr_t, new_idx, len(new_playlist)), _extract_preview_url(curr_t), new_playlist, new_idx, gr.update(choices=new_choices, value=new_sel)
            else:
                if isinstance(result, (tuple, list)) and len(result) >= 2:
                    reply_text = str(result[0] or "")
                    candidate_tracks = _normalize_tracks(result[1])
                    if candidate_tracks:
                        new_playlist = candidate_tracks
                        new_idx = 0
                elif isinstance(result, dict) and "reply" in result:
                    reply_text = str(result.get("reply", "") or "")
                    candidate_tracks = _normalize_tracks(result.get("tracks") or result.get("track"))
                    if candidate_tracks:
                        new_playlist = candidate_tracks
                        new_idx = 0
                else:
                    reply_text = str(result or "")

                curr_t = new_playlist[new_idx] if (new_playlist and 0 <= new_idx < len(new_playlist)) else None
                new_choices = _build_dropdown_choices(new_playlist)
                new_sel = new_choices[new_idx] if (new_choices and 0 <= new_idx < len(new_choices)) else None

                if not reply_text.strip():
                    if new_playlist:
                        reply_text = f"Carreguei **{len(new_playlist)} prévias de músicas** no player abaixo."
                    else:
                        reply_text = "Processado com sucesso."

                if new_playlist:
                    print(f"▶️ [Chat UI] {len(new_playlist)} faixa(s) sincronizada(s) com o player de prévias.", flush=True)

                print(f"🎧 [Chat UI] Exibindo resposta no chat ({len(reply_text)} caracteres)...", flush=True)

                # Efeito visual de digitação
                import time
                words = reply_text.split(" ")
                accumulated = ""
                for i, word in enumerate(words):
                    accumulated += (word if i == 0 else " " + word)
                    history[-1]["content"] = accumulated
                    yield "", history, _format_track_html(curr_t, new_idx, len(new_playlist)), _extract_preview_url(curr_t), new_playlist, new_idx, gr.update(choices=new_choices, value=new_sel)
                    time.sleep(0.015)

            print(f"✅ [Chat UI] Turno finalizado com sucesso.\n", flush=True)


        # Ações de envio
        turn_inputs = [msg_input, chatbot, playlist_state, current_index_state]
        turn_outputs = [msg_input, chatbot, track_display, audio_player, playlist_state, current_index_state, track_dropdown]

        msg_input.submit(
            fn=process_turn,
            inputs=turn_inputs,
            outputs=turn_outputs
        )
        send_btn.click(
            fn=process_turn,
            inputs=turn_inputs,
            outputs=turn_outputs
        )

        # Ações de alternância de faixas na playlist
        prev_btn.click(
            fn=switch_track_prev,
            inputs=[playlist_state, current_index_state],
            outputs=[track_display, audio_player, current_index_state, track_dropdown]
        )
        next_btn.click(
            fn=switch_track_next,
            inputs=[playlist_state, current_index_state],
            outputs=[track_display, audio_player, current_index_state, track_dropdown]
        )
        track_dropdown.input(
            fn=on_track_select,
            inputs=[track_dropdown, playlist_state],
            outputs=[track_display, audio_player, current_index_state]
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
    from .env_setup import ensure_mongodb_running
    if not ensure_mongodb_running():
        print("\n⚠️ " + "=" * 63, flush=True)
        print("⚠️ [AVISO] MongoDB não está rodando em localhost:27017!", flush=True)
        print("   As Tools que consultam o banco falharão com 'Connection Refused'.", flush=True)
        print("   👉 Para iniciar e restaurar o banco, execute antes:", flush=True)
        print("      from mcp_utils import prepare_environment", flush=True)
        print("      prepare_environment()", flush=True)
        print("=" * 66 + "\n", flush=True)

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



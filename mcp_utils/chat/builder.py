import html
import inspect
from typing import Any, Callable, Dict, List, Optional

import gradio as gr

from .styles import SPOTIFY_CSS
from .player import (
    normalize_tracks,
    build_dropdown_choices,
    get_index_from_selection,
    format_track_html,
    extract_preview_url,
)


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
            from ..agent import MCPAgent
            try:
                agent = MCPAgent(server=server, model=model)
                actual_chat_fn = agent.chat
            except Exception as e:
                def agent_init_err(user_msg: str, history: list):
                    return f"⚠️ Não foi possível iniciar o agente: {e}"
                actual_chat_fn = agent_init_err
        else:
            from ..llm.setup import get_openai_client

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

        # Banner de Ferramentas, Recursos e Prompts MCP conectados (se server foi passado)
        tools_list = []
        resources_list = []
        prompts_list = []
        if server is not None:
            if hasattr(server, "_tool_manager") and hasattr(server._tool_manager, "_tools"):
                for name, t in server._tool_manager._tools.items():
                    desc = getattr(t, "description", "") or ""
                    desc_str = f" ({desc.strip()})" if desc else ""
                    tools_list.append(f"<code>{html.escape(name)}</code>{html.escape(desc_str)}")
            if hasattr(server, "_resource_manager") and hasattr(server._resource_manager, "_templates"):
                for uri_tpl in server._resource_manager._templates.keys():
                    resources_list.append(f"<code>{html.escape(uri_tpl)}</code>")
            if hasattr(server, "_prompt_manager") and hasattr(server._prompt_manager, "_prompts"):
                for name, p in server._prompt_manager._prompts.items():
                    desc = getattr(p, "description", "") or ""
                    desc_str = f" ({desc.strip()})" if desc else ""
                    prompts_list.append(f"<code>{html.escape(name)}</code>{html.escape(desc_str)}")

        if tools_list or resources_list or prompts_list:
            banner_html = "<div style='background: #181818; border: 1px solid #282828; border-radius: 10px; padding: 12px 18px; margin-bottom: 12px; font-size: 13px;'>"
            if tools_list:
                banner_html += f"<div style='margin-bottom: 4px;'><strong style='color: #1DB954;'>🛠️ Ferramentas MCP Ativas ({len(tools_list)}):</strong> " + " • ".join(tools_list) + "</div>"
            if resources_list:
                banner_html += f"<div style='margin-bottom: 4px;'><strong style='color: #3b82f6;'>📖 Recursos MCP:</strong> " + " • ".join(resources_list) + "</div>"
            if prompts_list:
                banner_html += f"<div><strong style='color: #f59e0b;'>💡 Prompts MCP ({len(prompts_list)}):</strong> " + " • ".join(prompts_list) + "</div>"
            banner_html += "</div>"
            gr.HTML(banner_html)

        # Janela do Chat
        chatbot = gr.Chatbot(
            elem_id="music-chatbot",
            height=460,
        )

        # Seção de Prompts MCP interativos (se o servidor possuir prompts registrados)
        prompt_items = []
        if server is not None and hasattr(server, "_prompt_manager") and hasattr(server._prompt_manager, "_prompts"):
            prompt_items = list(server._prompt_manager._prompts.items())

        if prompt_items:
            with gr.Accordion("💡 Prompts MCP (Modelos de Mensagens Reutilizáveis)", open=False):
                with gr.Row():
                    prompt_dropdown = gr.Dropdown(
                        label="Selecionar Prompt MCP:",
                        choices=[(f"{name} — {getattr(p, 'description', '')}", name) for name, p in prompt_items],
                        value=prompt_items[0][0] if prompt_items else None,
                        scale=5,
                    )
                    prompt_arg_input = gr.Textbox(
                        label="Parâmetro(s) do Prompt (separe por vírgula se houver mais de um):",
                        placeholder="Ex: The Beatles, Oasis, Radiohead...",
                        scale=3,
                    )
                    load_prompt_btn = gr.Button("Carregar na Mensagem 📋", variant="secondary", scale=2)

                def load_selected_prompt(p_name: str, p_arg: str):
                    if not p_name or not server or not hasattr(server, "_prompt_manager"):
                        return ""
                    p = server._prompt_manager._prompts.get(p_name)
                    if not p:
                        return ""
                    args = {}
                    p_args = p.arguments or []
                    user_parts = [part.strip() for part in p_arg.split(",") if part.strip()] if p_arg else []

                    for idx, a in enumerate(p_args):
                        if idx < len(user_parts):
                            args[a.name] = user_parts[idx]
                        elif p_arg and p_arg.strip() and len(p_args) == 1:
                            args[a.name] = p_arg.strip()
                        else:
                            args[a.name] = f"[{a.name}]"

                    try:
                        from ..agent.core import _run_sync
                        async def _render():
                            res = await server.get_prompt(p_name, arguments=args)
                            if res and res.messages:
                                m = res.messages[0]
                                return m.content.text if hasattr(m.content, "text") else str(m.content)
                            return ""
                        return _run_sync(_render)
                    except Exception as err:
                        return f"Erro ao renderizar prompt '{p_name}': {err}"

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

        # Conectar ação do botão de Prompt (se existir)
        if prompt_items:
            load_prompt_btn.click(
                fn=load_selected_prompt,
                inputs=[prompt_dropdown, prompt_arg_input],
                outputs=[msg_input]
            )

        # Barra do Player Spotify (Dock Inferior com Playlist de Prévias)
        with gr.Group(elem_id="spotify-player-bar"):
            with gr.Row():
                gr.Markdown("#### 🎧 Player de Prévias Musicais (30s)")
            with gr.Row(elem_classes=["spotify-player-row"]):
                # Coluna 1: Card da Faixa (Capa, Título, Artista, Badge de Prévia 30s)
                with gr.Column(scale=5, min_width=270):
                    track_display = gr.HTML(value=format_track_html(None))
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
                return format_track_html(None), None, 0, gr.update(choices=[], value=None)
            new_idx = (current_idx - 1) % len(playlist)
            track = playlist[new_idx]
            choices = build_dropdown_choices(playlist)
            sel_val = choices[new_idx] if new_idx < len(choices) else None
            return (
                format_track_html(track, new_idx, len(playlist)),
                extract_preview_url(track),
                new_idx,
                gr.update(value=sel_val),
            )

        def switch_track_next(playlist: list, current_idx: int):
            playlist = playlist or []
            if not playlist:
                return format_track_html(None), None, 0, gr.update(choices=[], value=None)
            new_idx = (current_idx + 1) % len(playlist)
            track = playlist[new_idx]
            choices = build_dropdown_choices(playlist)
            sel_val = choices[new_idx] if new_idx < len(choices) else None
            return (
                format_track_html(track, new_idx, len(playlist)),
                extract_preview_url(track),
                new_idx,
                gr.update(value=sel_val),
            )

        def on_track_select(selection: Optional[str], playlist: list):
            playlist = playlist or []
            if not playlist or not selection:
                return format_track_html(None), None, 0
            choices = build_dropdown_choices(playlist)
            new_idx = get_index_from_selection(selection, choices)
            if new_idx < 0 or new_idx >= len(playlist):
                new_idx = 0
            track = playlist[new_idx]
            return (
                format_track_html(track, new_idx, len(playlist)),
                extract_preview_url(track),
                new_idx,
            )

        def process_turn(user_msg: str, history: list, playlist: list, current_idx: int):
            playlist = playlist or []
            curr_track = playlist[current_idx] if (playlist and 0 <= current_idx < len(playlist)) else None
            choices = build_dropdown_choices(playlist)
            sel_val = choices[current_idx] if (choices and 0 <= current_idx < len(choices)) else None

            if not user_msg or not user_msg.strip():
                yield "", history, format_track_html(curr_track, current_idx, len(playlist)), extract_preview_url(curr_track), playlist, current_idx, gr.update(choices=choices, value=sel_val)
                return

            print(f"\n🎧 [Chat UI] Processando mensagem do usuário: \"{user_msg}\"", flush=True)
            history = history or []
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": "..."})
            yield "", history, format_track_html(curr_track, current_idx, len(playlist)), extract_preview_url(curr_track), playlist, current_idx, gr.update(choices=choices, value=sel_val)

            try:
                result = actual_chat_fn(user_msg, history[:-2])
            except Exception as e:
                import traceback
                print(f"❌ [Chat UI Error] Exceção ao executar o chat: {e}", flush=True)
                traceback.print_exc()
                history[-1]["content"] = f"⚠️ Erro ao processar mensagem com o agente: {e}"
                yield "", history, format_track_html(curr_track, current_idx, len(playlist)), extract_preview_url(curr_track), playlist, current_idx, gr.update(choices=choices, value=sel_val)
                return

            new_playlist = playlist
            new_idx = current_idx

            # Se for um generator/iterator (streaming token a token)
            if inspect.isgenerator(result) or inspect.isgeneratorfunction(actual_chat_fn):
                for chunk in result:
                    if isinstance(chunk, (tuple, list)) and len(chunk) >= 2:
                        reply_part = str(chunk[0])
                        candidate_tracks = normalize_tracks(chunk[1])
                        if candidate_tracks:
                            new_playlist = candidate_tracks
                            new_idx = 0
                    else:
                        reply_part = str(chunk)

                    history[-1]["content"] = reply_part
                    curr_t = new_playlist[new_idx] if (new_playlist and 0 <= new_idx < len(new_playlist)) else None
                    new_choices = build_dropdown_choices(new_playlist)
                    new_sel = new_choices[new_idx] if (new_choices and 0 <= new_idx < len(new_choices)) else None
                    yield "", history, format_track_html(curr_t, new_idx, len(new_playlist)), extract_preview_url(curr_t), new_playlist, new_idx, gr.update(choices=new_choices, value=new_sel)
            else:
                if isinstance(result, (tuple, list)) and len(result) >= 2:
                    reply_text = str(result[0] or "")
                    candidate_tracks = normalize_tracks(result[1])
                    if candidate_tracks:
                        new_playlist = candidate_tracks
                        new_idx = 0
                elif isinstance(result, dict) and "reply" in result:
                    reply_text = str(result.get("reply", "") or "")
                    candidate_tracks = normalize_tracks(result.get("tracks") or result.get("track"))
                    if candidate_tracks:
                        new_playlist = candidate_tracks
                        new_idx = 0
                else:
                    reply_text = str(result or "")

                curr_t = new_playlist[new_idx] if (new_playlist and 0 <= new_idx < len(new_playlist)) else None
                new_choices = build_dropdown_choices(new_playlist)
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
                    yield "", history, format_track_html(curr_t, new_idx, len(new_playlist)), extract_preview_url(curr_t), new_playlist, new_idx, gr.update(choices=new_choices, value=new_sel)
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

        def on_clear():
            return "", [], format_track_html(None), None, [], 0, gr.update(choices=[], value=None)

        clear_btn.click(
            fn=on_clear,
            inputs=[],
            outputs=[msg_input, chatbot, track_display, audio_player, playlist_state, current_index_state, track_dropdown]
        )

    return demo

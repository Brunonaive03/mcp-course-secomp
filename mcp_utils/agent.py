import anyio
import inspect
import json
import re
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


DEFAULT_SYSTEM_PROMPT = """Você é um assistente especializado em música para o curso de MCP (Model Context Protocol).
Você tem acesso a ferramentas (tools) para pesquisar faixas, álbuns e resenhas.
Sempre utilize as ferramentas disponíveis quando o usuário solicitar informações sobre músicas ou pedir para tocar uma faixa.
Quando encontrar uma música adequada, responda de forma prestativa e amigável.
"""


class MCPAgent:
    """
    Agente MCP didático para o Google Colab e interfaces de Chat (Gradio).

    Conecta um servidor MCP (definido em memória no runtime do Colab ou em script)
    ao cliente LLM (Ollama Cloud) e faz a ponte com o player estilo Spotify.
    """

    def __init__(
        self,
        server: Any = None,
        server_script: Optional[str] = None,
        llm_client: Any = None,
        model: Optional[str] = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ):
        """
        Parâmetros:
        - `server`: Instância do servidor MCP definida em memória (MCPServer ou Server).
        - `server_script`: Caminho opcional para script Python caso queira usar stdio clássico via arquivo.
        - `llm_client`: Cliente OpenAI-compatible (ex: retornado por `get_ollama_client()`).
        - `model`: Nome do modelo (padrão: client.default_model ou 'llama3.2').
        - `system_prompt`: Prompt de sistema para instruir o comportamento do assistente.
        """
        if server is None and server_script is None:
            raise ValueError(
                "Você deve fornecer um servidor MCP: passe a instância `server` (definida no Colab) "
                "ou o caminho de um script via `server_script`."
            )

        self.server = server
        self.server_script = server_script
        self.system_prompt = system_prompt

        # Configurar cliente LLM
        if llm_client is None:
            import os
            from .llm_setup import get_openai_client, get_ollama_client
            if os.environ.get("OLLAMA_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
                self.llm_client = get_ollama_client()
            else:
                self.llm_client = get_openai_client()
        else:
            self.llm_client = llm_client

        # Modelo
        self.model = model or getattr(self.llm_client, "default_model", "gpt-oss:20b")


    def _get_lowlevel_server(self) -> Any:
        """Extrai a instância de servidor baixo-nível para conexão via streams de memória."""
        if hasattr(self.server, "_lowlevel_server"):
            return self.server._lowlevel_server
        return self.server

    async def _run_session(self, callback: Callable[[ClientSession], Any]) -> Any:
        """
        Executa uma sessão com o servidor MCP:
        - Se `server` for passado: conecta via memory streams (o transporte mais seguro no Colab).
        - Se `server_script` for passado: conecta via stdio_client (subprocesso).
        """
        if self.server is not None:
            lowlevel = self._get_lowlevel_server()
            # Criar par de canais de streaming de memória
            client_write, server_read = anyio.create_memory_object_stream(20)
            server_write, client_read = anyio.create_memory_object_stream(20)

            result = None
            async with anyio.create_task_group() as tg:
                # Inicia o servidor conectado aos streams
                init_options = lowlevel.create_initialization_options()
                tg.start_soon(lowlevel.run, server_read, server_write, init_options)

                try:
                    # Conecta o cliente aos streams correspondentes
                    async with ClientSession(client_read, client_write) as session:
                        await session.initialize()
                        result = await callback(session)
                finally:
                    tg.cancel_scope.cancel()
                    await client_write.aclose()
                    await server_write.aclose()
            return result

        elif self.server_script is not None:
            params = StdioServerParameters(command=sys.executable, args=[self.server_script])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await callback(session)

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Descobre e lista todas as tools registradas no servidor MCP."""
        async def _list(session: ClientSession):
            res = await session.list_tools()
            return [
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": getattr(t, "input_schema", getattr(t, "inputSchema", {})),
                }
                for t in res.tools
            ]

        return anyio.run(self._run_session, _list)

    def get_available_resources(self) -> List[Dict[str, Any]]:
        """Descobre e lista todos os resources registrados no servidor MCP."""
        async def _list(session: ClientSession):
            res = await session.list_resources()
            return [
                {
                    "uri": str(r.uri),
                    "name": r.name,
                    "description": r.description,
                    "mimeType": getattr(r, "mime_type", getattr(r, "mimeType", None)),
                }
                for r in res.resources
            ]

        return anyio.run(self._run_session, _list)

    def read_resource(self, uri: str) -> Optional[str]:
        """
        Lê o conteúdo textual de um Resource MCP registrado no servidor a partir de sua URI.

        Exemplo:
            agent.read_resource("music://tracks/trk_1dcdf5eadf")
        """
        async def _read(session: ClientSession):
            res = await session.read_resource(uri)
            if res.contents:
                c = res.contents[0]
                if hasattr(c, "text"):
                    return c.text
            return None

        return anyio.run(self._run_session, _read)

    def get_available_prompts(self) -> List[Dict[str, Any]]:
        """Descobre e lista todos os prompts registrados no servidor MCP."""
        async def _list(session: ClientSession):
            res = await session.list_prompts()
            prompts = []
            for p in res.prompts:
                args = []
                for a in (p.arguments or []):
                    if hasattr(a, "model_dump"):
                        args.append(a.model_dump())
                    elif hasattr(a, "dict"):
                        args.append(a.dict())
                    else:
                        args.append(dict(a))
                prompts.append({
                    "name": p.name,
                    "description": p.description,
                    "arguments": args,
                })
            return prompts

        return anyio.run(self._run_session, _list)

    def get_prompt(self, name: str, arguments: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
        """
        Recupera as mensagens renderizadas de um Prompt registrado no servidor MCP.

        Retorna lista de dicionários com 'role' e 'content'.
        Exemplo:
            messages = agent.get_prompt("discover_artist", {"artist": "Oasis"})
        """
        async def _get(session: ClientSession):
            res = await session.get_prompt(name, arguments=arguments)
            rendered_messages = []
            for m in res.messages:
                text = ""
                if hasattr(m.content, "text"):
                    text = m.content.text
                elif isinstance(m.content, str):
                    text = m.content
                else:
                    text = str(m.content)
                rendered_messages.append({
                    "role": m.role,
                    "content": text
                })
            return rendered_messages

        return anyio.run(self._run_session, _get)

    def _convert_mcp_to_openai_tools(self, mcp_tools: list) -> list:
        """Converte as ferramentas MCP para o formato de function calling da OpenAI/Ollama."""
        openai_tools = []
        for t in mcp_tools:
            params = getattr(t, "input_schema", getattr(t, "inputSchema", {})) or {"type": "object", "properties": {}}
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": params,
                }
            })
        return openai_tools


    def _extract_tracks_from_tool_result(self, raw_result: Any) -> List[Any]:
        """Tenta extrair metadados ou IDs de todas as faixas a partir do retorno da tool do MCP."""
        if not raw_result or not hasattr(raw_result, "content"):
            return []

        tracks: List[Any] = []
        for item in raw_result.content:
            if isinstance(item, TextContent) and item.text:
                text = item.text.strip()
                # 1. Tentar parsear JSON
                try:
                    data = json.loads(text)
                    if isinstance(data, list):
                        for el in data:
                            if isinstance(el, dict):
                                tracks.append(el)
                            elif isinstance(el, str) and el.startswith("trk_"):
                                tracks.append(el)
                    elif isinstance(data, dict):
                        tracks.append(data)
                except Exception:
                    pass

                # 2. Se não encontrou no JSON, busca por IDs no formato trk_...
                if not tracks:
                    matches = re.findall(r"trk_[a-zA-Z0-9]+", text)
                    if matches:
                        seen = set()
                        for m in matches:
                            if m not in seen:
                                seen.add(m)
                                tracks.append(m)

        return tracks

    def _extract_track_from_tool_result(self, raw_result: Any) -> Optional[Any]:
        """Tenta extrair metadados ou ID de faixa (primeiro item) a partir do retorno da tool."""
        tracks = self._extract_tracks_from_tool_result(raw_result)
        return tracks[0] if tracks else None

    async def _chat_async(self, message: str, history: Optional[list] = None) -> Tuple[str, List[Any]]:
        """Loop de execução assíncrona do agente com tool-calling."""
        print(f"\n" + "=" * 60, flush=True)
        print(f"🎵 [MCP Host] Mensagem recebida: \"{message}\"", flush=True)
        detected_tracks: List[Any] = []

        async def _step(session: ClientSession):
            nonlocal detected_tracks

            # 1. Descoberta de Tools no Servidor MCP
            print(f"🔍 [MCP Host] Descobrindo ferramentas no servidor MCP...", flush=True)
            tools_resp = await session.list_tools()
            openai_tools = self._convert_mcp_to_openai_tools(tools_resp.tools)
            tool_names = [t.name for t in tools_resp.tools]
            print(f"🛠️ [MCP Host] {len(tool_names)} ferramenta(s) registrada(s): {tool_names}", flush=True)

            # 2. Montar histórico de mensagens
            messages = [{"role": "system", "content": self.system_prompt}]
            if history:
                for turn in history:
                    role = turn.get("role")
                    content = turn.get("content")
                    if role in ["user", "assistant"] and content:
                        messages.append({"role": role, "content": content})

            messages.append({"role": "user", "content": message})

            # 3. Primeira chamada à LLM
            call_kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
            }
            if openai_tools:
                call_kwargs["tools"] = openai_tools
                call_kwargs["tool_choice"] = "auto"

            print(f"🤖 [MCP Host] Consultando modelo '{self.model}'...", flush=True)
            try:
                response = self.llm_client.chat.completions.create(**call_kwargs)
            except Exception as e:
                print(f"❌ [MCP Host] Erro na requisição à LLM: {e}", flush=True)
                raise e

            choice = response.choices[0]
            assistant_msg = choice.message
            tool_calls = getattr(assistant_msg, "tool_calls", None)

            # 4. Verificar se a LLM solicitou chamada de Tool
            if tool_calls:
                print(f"⚡ [MCP Host] A LLM decidiu invocar {len(tool_calls)} Tool(s)!", flush=True)
                
                # Adiciona a intenção da LLM no histórico como dicionário estruturado e serializável
                assistant_tool_calls = []
                for i, tc in enumerate(tool_calls):
                    call_id = getattr(tc, "id", None) or f"call_{i}"
                    assistant_tool_calls.append({
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    })

                messages.append({
                    "role": "assistant",
                    "content": assistant_msg.content or "",
                    "tool_calls": assistant_tool_calls,
                })

                last_result_text = ""
                for i, tool_call in enumerate(tool_calls):
                    fn_name = tool_call.function.name
                    call_id = getattr(tool_call, "id", None) or f"call_{i}"
                    try:
                        fn_args = json.loads(tool_call.function.arguments or "{}")
                    except Exception:
                        fn_args = {}

                    print(f"   ▶️ [Execução de Tool] {fn_name}({fn_args})", flush=True)

                    # Executa a tool no Servidor MCP
                    try:
                        tool_result = await session.call_tool(fn_name, fn_args)
                    except Exception as err:
                        tool_result = None
                        result_text = f"Erro ao executar a ferramenta {fn_name}: {err}"
                        print(f"   ❌ [Erro na Tool] Falha ao rodar '{fn_name}': {err}", flush=True)

                    if tool_result:
                        # Intercepta se a tool retornou informações de música
                        tracks_cand = self._extract_tracks_from_tool_result(tool_result)
                        if tracks_cand:
                            print(f"   🎵 [MCP Host] {len(tracks_cand)} faixa(s) detectada(s) no retorno da Tool.", flush=True)
                            for cand in tracks_cand:
                                track_id = None
                                if isinstance(cand, str) and cand.startswith("trk_"):
                                    track_id = cand
                                elif isinstance(cand, dict):
                                    track_id = cand.get("track_id") or cand.get("_id")

                                resolved_track = cand
                                if track_id:
                                    print(f"   🎯 [MCP Host] ID identificado: '{track_id}'. Resolvendo via MCP Resource...", flush=True)
                                    resource_uri = f"music://tracks/{track_id}"
                                    try:
                                        resource_res = await session.read_resource(resource_uri)
                                        if resource_res and resource_res.contents:
                                            c = resource_res.contents[0]
                                            if hasattr(c, "text") and c.text:
                                                res_data = json.loads(c.text)
                                                if isinstance(res_data, dict):
                                                    resolved_track = res_data
                                                    print(f"   ✅ [MCP Resource] Recurso '{resource_uri}' resolvido via MCP.", flush=True)
                                    except Exception as r_err:
                                        print(f"   ℹ️ [MCP Resource] Aviso ao ler '{resource_uri}': {r_err}. Mantendo dados da Tool.", flush=True)

                                detected_tracks.append(resolved_track)

                            # Deduplica faixas por ID ou título mantendo a ordem
                            seen_ids = set()
                            unique_tracks = []
                            for t in detected_tracks:
                                tid = (t.get("track_id") or t.get("_id") or t.get("title")) if isinstance(t, dict) else str(t)
                                if tid not in seen_ids:
                                    seen_ids.add(tid)
                                    unique_tracks.append(t)
                            detected_tracks = unique_tracks

                        # Converte conteúdo do resultado para texto
                        result_text_parts = []
                        for c in getattr(tool_result, "content", []):
                            if hasattr(c, "text"):
                                result_text_parts.append(c.text)
                        result_text = "\n".join(result_text_parts) or "Sucesso."
                        print(f"   ✅ [Retorno da Tool] ({len(result_text)} caracteres): {result_text[:120]}...", flush=True)

                    last_result_text = result_text

                    # Adiciona a resposta da ferramenta para a LLM
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": result_text,
                    })

                # Segunda chamada para a LLM gerar a resposta final com os dados da tool
                final_call_kwargs: Dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                }
                if openai_tools:
                    final_call_kwargs["tools"] = openai_tools

                print(f"🤖 [MCP Host] Enviando dados da Tool de volta para o modelo '{self.model}'...", flush=True)
                try:
                    final_resp = self.llm_client.chat.completions.create(**final_call_kwargs)
                    final_msg = final_resp.choices[0].message
                    final_text = (
                        final_msg.content
                        or getattr(final_msg, "reasoning_content", None)
                        or getattr(final_msg, "reasoning", None)
                        or ""
                    )
                    print(f"📥 [MCP Host] Resposta recebida da LLM.", flush=True)
                except Exception as e:
                    print(f"⚠️ [MCP Host] Falha na segunda chamada da LLM: {e}. Usando sintetizador local.", flush=True)
                    final_text = ""

                # Fallback amigável caso modelos de raciocínio (como gpt-oss) deixem content vazio
                if not final_text or not final_text.strip():
                    print(f"ℹ️ [MCP Host] LLM não gerou texto conversacional. Sintetizando resposta amigável a partir dos dados...", flush=True)
                    if detected_tracks:
                        if len(detected_tracks) == 1:
                            t = detected_tracks[0]
                            t_name = t.get("title", "faixa selecionada") if isinstance(t, dict) else str(t)
                            t_artists = (t.get("artists") or [t.get("artist", "")]) if isinstance(t, dict) else []
                            artist_names = ", ".join(str(a) for a in t_artists if a)
                            if artist_names:
                                final_text = f"Encontrei a música **{t_name}** de **{artist_names}** no catálogo! A prévia de 30 segundos já está disponível no player abaixo."
                            else:
                                final_text = f"Encontrei a faixa **{t_name}** no catálogo! A prévia já está disponível no player abaixo."
                        else:
                            items = []
                            for idx, t in enumerate(detected_tracks):
                                if isinstance(t, dict):
                                    title = t.get("title", f"Faixa {idx+1}")
                                    artists = t.get("artists") or [t.get("artist", "")]
                                    art_str = f" ({', '.join(str(a) for a in artists if a)})" if artists else ""
                                    items.append(f"{idx+1}. **{title}**{art_str}")
                                else:
                                    items.append(f"{idx+1}. **{t}**")
                            final_text = (
                                f"Encontrei **{len(detected_tracks)} faixas** no catálogo! Você pode ouvir as prévias de 30 segundos e alternar entre elas no player abaixo:\n\n"
                                + "\n".join(items)
                            )
                    elif last_result_text and last_result_text != "Sucesso.":
                        try:
                            parsed = json.loads(last_result_text)
                            if isinstance(parsed, list) and len(parsed) > 0:
                                items = []
                                for idx, item in enumerate(parsed):
                                    if isinstance(item, dict):
                                        title = item.get("title", f"Faixa {idx+1}")
                                        artists = item.get("artists", [])
                                        art_str = f" ({', '.join(artists)})" if artists else ""
                                        items.append(f"{idx+1}. **{title}**{art_str}")
                                if items:
                                    final_text = "Encontrei as seguintes faixas:\n" + "\n".join(items)
                        except Exception:
                            pass
                        if not final_text:
                            final_text = f"Resultado da consulta:\n{last_result_text}"
                    else:
                        final_text = "Consulta realizada com sucesso."

                print(f"💬 [MCP Host] Resposta final do assistente: \"{final_text[:100]}...\"", flush=True)
                print("=" * 60 + "\n", flush=True)
                return final_text

            else:
                resp_text = (
                    assistant_msg.content
                    or getattr(assistant_msg, "reasoning_content", None)
                    or getattr(assistant_msg, "reasoning", None)
                    or "Olá! Como posso ajudar você com músicas hoje?"
                )
                print(f"💬 [MCP Host] Resposta direta (sem ferramentas): \"{resp_text[:100]}...\"", flush=True)
                print("=" * 60 + "\n", flush=True)
                return resp_text

        reply_text = await self._run_session(_step)
        return reply_text, detected_tracks

    def chat(self, message: str, history: Optional[list] = None) -> Tuple[str, List[Any]]:
        """
        Método de chat síncrono para ser passado diretamente ao `launch_music_chat`:

        Exemplo:
            agent = MCPAgent(server=meu_servidor, llm_client=client)
            launch_music_chat(agent.chat)
        """
        return anyio.run(self._chat_async, message, history)

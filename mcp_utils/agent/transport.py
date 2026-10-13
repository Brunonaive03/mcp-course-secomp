import anyio
import sys
from typing import Any, Callable, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def get_lowlevel_server(server: Any) -> Any:
    """Extrai a instância de servidor baixo-nível para conexão via streams de memória."""
    if hasattr(server, "_lowlevel_server"):
        return server._lowlevel_server
    return server


async def run_mcp_session(
    server: Any = None,
    server_script: Optional[str] = None,
    callback: Callable[[ClientSession], Any] = None,
) -> Any:
    """
    Executa uma sessão com o servidor MCP:
    - Se `server` for passado: conecta via memory streams (transporte ideal para Google Colab).
    - Se `server_script` for passado: conecta via stdio_client (subprocesso local).
    """
    if server is not None:
        lowlevel = get_lowlevel_server(server)
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

    elif server_script is not None:
        params = StdioServerParameters(command=sys.executable, args=[server_script])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await callback(session)
    else:
        raise ValueError("É necessário fornecer um servidor MCP ('server' ou 'server_script').")

from typing import Any, Dict, List


def convert_mcp_to_openai_tools(mcp_tools: list) -> List[Dict[str, Any]]:
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

import json
import re
from typing import Any, List, Optional
from mcp.types import TextContent


def _is_valid_track_dict(d: dict) -> bool:
    """Verifica se um dicionário representa de fato metadados de uma faixa musical."""
    if not isinstance(d, dict):
        return False
    # Descarta objetos que representam resenhas, status ou mensagens informativas
    if any(k in d for k in ("reviewer", "comment", "score", "rating", "review_id", "status")):
        return False
    # Faixa com ID explícito no padrão do catálogo
    tid = str(d.get("track_id") or d.get("_id") or "")
    if tid.startswith("trk_"):
        return True
    # Faixa com recursos multimídia ou com título e artistas
    if "resources" in d:
        return True
    if "title" in d and ("artists" in d or "artist" in d):
        return True
    return False


def extract_tracks_from_tool_result(raw_result: Any) -> List[Any]:
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
                        if isinstance(el, dict) and _is_valid_track_dict(el):
                            tracks.append(el)
                        elif isinstance(el, str) and el.startswith("trk_"):
                            tracks.append(el)
                elif isinstance(data, dict) and _is_valid_track_dict(data):
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


def extract_track_from_tool_result(raw_result: Any) -> Optional[Any]:
    """Tenta extrair metadados ou ID de faixa (primeiro item) a partir do retorno da tool."""
    tracks = extract_tracks_from_tool_result(raw_result)
    return tracks[0] if tracks else None

import html
from typing import Any, Dict, List, Optional


def normalize_track(track_data: Any) -> Optional[Dict[str, Any]]:
    """Normaliza um único registro de faixa recebido do agente ou do recurso MCP."""
    if not track_data:
        return None

    if isinstance(track_data, str) and track_data.strip().startswith("trk_"):
        track_id = track_data.strip()
        return {"title": track_id, "artists": ["Faixa MCP"], "resources": {}, "track_id": track_id}

    if isinstance(track_data, dict):
        return track_data

    return None


def normalize_tracks(candidate: Any) -> List[Dict[str, Any]]:
    """Normaliza faixas recebidas (única ou lista) para uma lista de dicionários."""
    if not candidate:
        return []

    tracks: List[Dict[str, Any]] = []
    if isinstance(candidate, (list, tuple)):
        for item in candidate:
            norm = normalize_track(item)
            if norm:
                tracks.append(norm)
    else:
        norm = normalize_track(candidate)
        if norm:
            tracks.append(norm)

    return tracks


def build_dropdown_choices(playlist: List[Dict[str, Any]]) -> List[str]:
    """Gera lista de rótulos formatados para o dropdown da playlist, indicando se possui áudio."""
    choices = []
    for i, t in enumerate(playlist):
        title = t.get("title", f"Faixa {i+1}")
        artists = t.get("artists") or [t.get("artist", "")]
        art_str = f" - {', '.join(str(a) for a in artists if a)}" if artists else ""
        res = t.get("resources") or {}
        has_audio = bool(res.get("preview_url") or t.get("preview_url"))
        audio_tag = "" if has_audio else " (sem áudio)"
        choices.append(f"{i+1}. {title}{art_str}{audio_tag}")
    return choices


def get_index_from_selection(selection: Optional[str], choices: List[str]) -> int:
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


def format_track_html(track: Optional[Dict[str, Any]], current_idx: int = 0, total_tracks: int = 0) -> str:
    """Gera o HTML do card de faixa do player com feedback dinâmico sobre recursos disponíveis (áudio e capa)."""
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
    preview_url = resources.get("preview_url") or track.get("preview_url") or ""

    if thumb_url:
        cover_html = f'<img src="{html.escape(thumb_url)}" class="spotify-cover-art" alt="Capa">'
    else:
        cover_html = '<div class="spotify-cover-art">🎧</div>'

    counter_badge = ""
    if total_tracks > 1:
        counter_badge = f'<span style="background: #282828; color: #1DB954; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;">Faixa {current_idx + 1} de {total_tracks}</span>'

    # Feedback dinâmico de acordo com os recursos disponíveis
    if preview_url:
        badge_html = '<span class="spotify-badge-preview">▶️ PRÉVIA DA MÚSICA (30s)</span>'
        note_html = '<p class="spotify-preview-note">⏱️ Amostra de áudio de 30s resolvida via MCP Resource</p>'
    elif thumb_url:
        badge_html = '<span class="spotify-badge-no-audio">🖼️ SEM PRÉVIA DE ÁUDIO</span>'
        note_html = '<p class="spotify-preview-note" style="color: #f59e0b;">ℹ️ Capa disponível, mas a faixa não possui amostra de áudio</p>'
    else:
        badge_html = '<span class="spotify-badge-meta-only">📄 APENAS METADADOS</span>'
        note_html = '<p class="spotify-preview-note" style="color: #727272;">⚠️ Faixa sem mídia registrada no catálogo</p>'

    return f"""
    <div class="spotify-track-container">
        {cover_html}
        <div class="spotify-track-meta">
            <div style="display: flex; align-items: center; gap: 8px;">
                {badge_html}
                {counter_badge}
            </div>
            <p class="spotify-track-title" title="{title}">{title}</p>
            <p class="spotify-track-artist" title="{artist_str}">{artist_str}</p>
            {note_html}
        </div>
    </div>
    """


def extract_preview_url(track: Optional[Dict[str, Any]]) -> Optional[str]:
    """Extrai a URL do preview em áudio."""
    if not track:
        return None
    resources = track.get("resources") or {}
    return resources.get("preview_url") or track.get("preview_url")


# Aliases internos para compatibilidade
_normalize_track = normalize_track
_normalize_tracks = normalize_tracks
_build_dropdown_choices = build_dropdown_choices
_get_index_from_selection = get_index_from_selection
_format_track_html = format_track_html
_extract_preview_url = extract_preview_url

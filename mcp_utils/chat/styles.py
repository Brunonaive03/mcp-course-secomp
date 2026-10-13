"""Estilos visuais (CSS) estilo Spotify Dark Theme para o MCP Music Chat."""

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

.spotify-badge-no-audio {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.5);
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.5px;
    display: inline-block;
}

.spotify-badge-meta-only {
    background: rgba(114, 114, 114, 0.15);
    color: #9e9e9e;
    border: 1px solid rgba(114, 114, 114, 0.4);
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

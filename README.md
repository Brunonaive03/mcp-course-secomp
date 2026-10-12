# MCP Course - Infraestrutura e Dados para Google Colab

Repositório unificado para o mini-curso sobre **Model Context Protocol (MCP)** na SECOMP UFPE. Este repositório fornece o pacote Python utilitário (`mcp_course_secomp`) e o dump de dados do MongoDB (`data/`) para que os alunos possam configurar e executar a infraestrutura de banco de dados diretamente no **Google Colab** de forma simples e automatizada.

---

## 📁 Estrutura do Projeto

```text
mcp-course-secomp/
├── data/                      # Dump do MongoDB (.bson e .metadata.json)
│   ├── albums.bson
│   ├── albums.metadata.json
│   ├── reviews.bson
│   ├── reviews.metadata.json
│   ├── tracks.bson
│   └── tracks.metadata.json
├── mcp_utils/                 # Pacote Python com utilitários
│   ├── __init__.py
│   ├── env_setup.py           # Automação do ambiente MongoDB no Colab
│   ├── llm_setup.py           # Conexão e autenticação com Ollama Cloud
│   ├── chat_ui.py             # Chat Gradio com player de música estilo Spotify
│   └── agent.py               # Agente MCP (conecta servidor ao Ollama e ao Chat)
├── setup.py                   # Configuração de empacotamento Python
└── README.md                  # Documentação do projeto
```

---

## 🚀 Como Usar no Google Colab

### 1. Instalação do Pacote

No notebook do Google Colab, instale o pacote diretamente a partir do repositório no GitHub:

```python
!pip install git+https://github.com/Brunonaive03/mcp-course-secomp.git
```

---

### 2. Preparar Banco de Dados MongoDB

Importe e execute `prepare_environment` para baixar o banco e iniciar o MongoDB com a coleção de músicas:

```python
from mcp_utils import prepare_environment

prepare_environment()
```

---

### 3. Configuração da Chave da API

Para utilizar o modelo `gpt-oss:20b` (modelo open-weights da OpenAI):

No Google Colab:
1. Abra a barra lateral esquerda e clique no ícone de Chave/Segredos (🔑).
2. Adicione o segredo:
   - **Nome**: `OPENAI_API_KEY` (ou `OLLAMA_API_KEY`)
   - **Valor**: `[Cole sua chave de API]`
3. Habilite a opção **"Acesso ao notebook"** (Notebook access).

*(Opcional) Para testar apenas o chat LLM imediatamente sem MCP:*
```python
from mcp_utils import launch_music_chat

# Inicia o chat imediatamente conectado ao gpt-oss:20b internamente!
launch_music_chat()
```

---

### 4. Construindo o Servidor MCP na Célula

Os alunos definem o Servidor MCP com **Tools** e **Resources** diretamente no runtime do Colab:

```python
import json
from pymongo import MongoClient
from mcp.server.mcpserver import MCPServer

# 1. Definir o Servidor MCP na célula e conectar ao banco local
server = MCPServer("mcp-music-lab")
mongo = MongoClient("mongodb://localhost:27017/")["mcp_music_lab"]

# 2. Tool MCP: O modelo descobre e chama para buscar faixas
@server.tool()
def search_tracks_by_artist(artist: str) -> str:
    """Busca até 3 faixas de um determinado artista no catálogo.
    
    Args:
        artist: Nome do artista ou banda (ex: 'Queen', 'Oasis').
    """
    cursor = mongo["tracks"].find(
        {"artists": {"$regex": artist, "$options": "i"}},
        {"_id": 1, "title": 1, "artists": 1}
    ).limit(3)
    results = [
        {"track_id": str(t["_id"]), "title": t["title"], "artists": t.get("artists", [])}
        for t in cursor
    ]
    return json.dumps(results, ensure_ascii=False) if results else "Nenhuma faixa encontrada."

# 3. Resource MCP: A aplicação lê via URI para carregar mídia e áudio no Player
@server.resource("music://tracks/{track_id}")
def get_track_resource(track_id: str) -> str:
    """Recurso consumido pela aplicação (Host) para obter áudio e capa da faixa."""
    track = mongo["tracks"].find_one({"_id": track_id})
    if track:
        return json.dumps(track, default=str)
    return "{}"
```

> **💡 Diferença Fundamental no MCP:**
> - **Tool (`search_tracks_by_artist`)**: Operação solicitada pelo **LLM**. O modelo decide quando chamar e recebe dados compactos no contexto para formular sua resposta ao usuário.
> - **Resource (`music://tracks/{track_id}`)**: Conteúdo lido pela **aplicação/Host** (`resources/read`). Quando o assistente identifica uma música, a aplicação resolve o recurso via protocolo MCP para obter a URL de streaming e a imagem da capa, alimentando o Player estilo Spotify.

---

### 5. Iniciar o Chat com Player Spotify e Servidor MCP

Basta passar o `server` para `launch_music_chat`. A biblioteca inicializa o agente com o `gpt-oss:20b`, executa o loop de ferramentas, resolve os recursos e toca as músicas no player automaticamente:

```python
from mcp_utils import launch_music_chat

# Conecta o servidor MCP ao chat com gpt-oss:20b e player Spotify
launch_music_chat(server=server)
```



---

## ⚙️ O que a função `prepare_environment` faz

A função detecta automaticamente a versão do Ubuntu do Colab (Noble 24.04 ou Jammy 22.04) e executa de forma sequencial e silenciosa:
1. **Chave GPG do MongoDB**: Adiciona a chave oficial do MongoDB (`pgp.mongodb.com`).
2. **Repositório APT**: Registra o repositório oficial do MongoDB compatível (`8.0` para Ubuntu 24.04 Noble, `7.0` para Ubuntu 22.04 Jammy).
3. **Instalação do MongoDB**: Executa `apt-get update` e instala os pacotes `mongodb-org` e `mongodb-database-tools`.
4. **Inicialização do `mongod`**: Cria o diretório `/data/db` e inicia o daemon em background com `--fork`.
5. **Download dos Dados**: Realiza `git clone` do repositório para obter os arquivos de dump da pasta `data/`.
6. **Restauração com `mongorestore`**: Restaura as coleções no banco `mcp_music_lab`.

---

## 🗄️ Banco de Dados

* **Database**: `mcp_music_lab`
* **Coleções**:
  * `albums`
  * `reviews`
  * `tracks` (com `title`, `artists`, `description`, `resources.thumbnail_url`, `resources.preview_url`)


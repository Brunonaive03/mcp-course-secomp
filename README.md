# MCP Course - Infraestrutura e Dados para Google Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Brunonaive03/mcp-course-secomp/blob/main/notebooks/minicurso_mcp.ipynb)

Repositório unificado para o mini-curso sobre **Model Context Protocol (MCP)** na SECOMP UFPE. Este repositório fornece o pacote Python utilitário (`mcp_course_secomp` / `mcp_utils`), os materiais didáticos na pasta `notebooks/` (com o notebook prático interativo `minicurso_mcp.ipynb` e os slides da apresentação `Introdução a MCP e LLMs.pdf`) e o dump de dados do MongoDB (`data/`) para que os alunos possam configurar e executar a infraestrutura de banco de dados diretamente no **Google Colab** de forma simples e automatizada.

---

## 📁 Estrutura do Projeto

```text
mcp-course-secomp/
├── notebooks/                 # Materiais didáticos (notebook prático e apresentação em PDF)
│   ├── minicurso_mcp.ipynb    # Notebook interativo para o Google Colab
│   └── Introdução a MCP e LLMs.pdf # Apresentação de slides do minicurso
├── data/                      # Dump do MongoDB (.bson e .metadata.json)
│   ├── albums.bson
│   ├── albums.metadata.json
│   ├── reviews.bson
│   ├── reviews.metadata.json
│   ├── tracks.bson
│   └── tracks.metadata.json
├── mcp_utils/                 # Pacote Python com utilitários (instalado via pip)
│   ├── env/
│   │   ├── __init__.py
│   │   └── setup.py           # Automação do ambiente MongoDB no Colab
│   ├── llm/
│   │   ├── __init__.py
│   │   └── setup.py           # Conexão e autenticação com Ollama Cloud
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── core.py            # Orquestrador MCPAgent e loop assíncrono de tool calling
│   │   ├── transport.py       # Conexão MCP (memória / stdio)
│   │   ├── schema.py          # Conversão de esquemas de tools para OpenAI
│   │   └── parser.py          # Extração e normalização de faixas musicais
│   └── chat/
│       ├── __init__.py
│       ├── launcher.py        # Inicialização do servidor Gradio (launch_music_chat)
│       ├── builder.py         # Montagem do layout Gradio e eventos do chat
│       ├── player.py          # Lógica do player Spotify, faixas e HTML
│       └── styles.py          # Estilos visuais CSS (Spotify Dark Theme)
├── MANIFEST.in                # Configuração para isolar notebooks/ e data/ do pacote pip
├── setup.py                   # Configuração de empacotamento Python
├── test_preview.py            # Script auxiliar para teste local da interface Gradio
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

Para utilizar o modelo `gpt-oss:20b` (modelo open-weights na Ollama Cloud):

No Google Colab:
1. Abra a barra lateral esquerda e clique no ícone de Chave/Segredos (🔑).
2. Adicione o segredo:
   - **Nome**: `OLLAMA_API_KEY` *(ou `OPENAI_API_KEY` se utilizar o endpoint oficial da OpenAI)*
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

Os alunos definem o Servidor MCP com **Tools**, **Resources** e **Prompts** diretamente no runtime do Colab:

```python
import json
import re
from datetime import datetime, timezone
from pymongo import MongoClient
from mcp.server.mcpserver import MCPServer
from pydantic import Field

# 1. Definir o Servidor MCP na célula e conectar ao banco local
server = MCPServer("mcp-music-lab")
mongo = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)["mcp_music_lab"]

# 2. Tool MCP: Busca faixas no catálogo (leitura compacta)
@server.tool()
def search_tracks_by_artist(
    artist: str = Field(..., description="Nome do artista ou banda (ex: 'The Beatles', 'Oasis')"),
    limit: int = Field(5, ge=1, le=20, description="Quantidade máxima de faixas a retornar")
) -> str:
    """Busca faixas de um determinado artista no catálogo."""
    cursor = mongo["tracks"].find(
        {"artists": {"$regex": re.escape(artist), "$options": "i"}},
        {"_id": 1, "title": 1, "artists": 1}
    ).limit(limit)
    results = [
        {"track_id": str(t["_id"]), "title": t["title"], "artists": t.get("artists", [])}
        for t in cursor
    ]
    return json.dumps(results, ensure_ascii=False) if results else f"Nenhuma faixa encontrada para '{artist}'."

# 3. Tool MCP: Adiciona resenha de álbum (escrita no banco)
@server.tool()
def add_album_review(
    album_title: str = Field(..., description="Título do álbum avaliado (ex: 'Abbey Road', 'Definitely Maybe')"),
    reviewer: str = Field(..., description="Nome do autor da resenha"),
    score: float = Field(..., ge=1, le=5, description="Nota de 1 a 5 (ex: 4, 4.5, 5)"),
    comment: str = Field(..., description="Comentário crítico sobre o álbum")
) -> str:
    """Registra uma nova resenha e avaliação crítica de álbum no banco de dados."""
    doc = {
        "album_title": album_title.strip(),
        "reviewer": reviewer.strip(),
        "score": float(score),
        "comment": comment.strip(),
        "created_at": datetime.now(timezone.utc)
    }
    res = mongo["reviews"].insert_one(doc)
    return json.dumps({"status": "success", "message": f"Resenha de '{album_title}' salva com sucesso!"})

# 4. Tool MCP: Consulta resenhas de álbuns
@server.tool()
def get_album_reviews(
    album_title: str = Field(..., description="Título aproximado do álbum")
) -> str:
    """Consulta avaliações e resenhas registradas sobre um álbum."""
    cursor = mongo["reviews"].find(
        {"album_title": {"$regex": re.escape(album_title), "$options": "i"}},
        {"_id": 0, "album_title": 1, "reviewer": 1, "score": 1, "comment": 1}
    ).limit(5)
    reviews = list(cursor)
    return json.dumps(reviews, ensure_ascii=False) if reviews else f"Nenhuma resenha encontrada para '{album_title}'."

# 5. Resource MCP: A aplicação lê via URI para carregar mídia e áudio no Player
@server.resource("music://tracks/{track_id}")
def get_track_resource(track_id: str) -> str:
    """Recurso consumido pela aplicação (Host) para obter áudio e capa da faixa."""
    track = mongo["tracks"].find_one({"_id": track_id})
    if track:
        return json.dumps(track, default=str)
    return "{}"

# 6. Prompt MCP: Modelo de mensagem acionado pelo usuário
@server.prompt()
def discover_artist(artist: str) -> str:
    """Roteiro de descoberta musical guiado para explorar um artista."""
    return f"Faça uma análise musical do artista '{artist}'. Apresente sua história brevemente, liste os sucessos presentes no catálogo e recomende uma faixa para começar a ouvir."
```

> **💡 A Trinca de Primitivas do MCP:**
> - **Tool (`search_tracks_by_artist`, `add_album_review`, `get_album_reviews`)**: Operação solicitada pelo **LLM**. O modelo decide autonomamente quando chamar e recebe dados compactos no contexto para formular sua resposta ao usuário.
> - **Resource (`music://tracks/{track_id}`)**: Conteúdo lido pela **aplicação/Host** (`resources/read`). Quando o assistente identifica as músicas, a aplicação resolve os recursos via protocolo MCP para obter as URLs das **prévias de áudio (30s)** e imagens de capa, alimentando a playlist do Player.
> - **Prompt (`discover_artist`)**: Modelo de instrução acionado pelo **Usuário** (`prompts/get`). O usuário escolhe na interface um modelo de mensagem pré-configurado e preenche os parâmetros para iniciar uma conversa estruturada.

---

### 5. Iniciar o Chat com Player de Prévias e Servidor MCP

Basta passar o `server` para `launch_music_chat`. A biblioteca inicializa o agente, lista as ferramentas conectadas, executa o loop de chamadas multi-turn, resolve as prévias de todas as faixas e permite alternar entre elas no player:

```python
from mcp_utils import launch_music_chat

# Conecta o servidor MCP ao chat com player de prévias (30s)
launch_music_chat(server=server)
```

> **⚠️ Atenção sobre Segurança (`share=True`):** Por padrão, no Colab o Gradio gera uma URL pública (`gradio.live`). Qualquer pessoa com esse link poderá enviar mensagens consumindo a cota da sua chave configurada. Para execução local ou fechada, utilize `launch_music_chat(server=server, share=False)`.

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
  * `albums` (`_id`, `title`, `artists`, `year`, `description`, `tracks`)
  * `reviews` (`album_title`, `reviewer`, `score`, `comment`, `created_at`) — *inicia vazia, populada pelos alunos via tool `add_album_review`*
  * `tracks` (`_id`, `album_id`, `title`, `artists`, `description`, `resources.thumbnail_url`, `resources.preview_url`)


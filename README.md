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
├── mcp_utils/                 # Pacote Python com scripts utilitários
│   ├── __init__.py
│   └── env_setup.py           # Script de automação do ambiente
├── setup.py                   # Configuração de empacotamento Python
└── README.md                  # Documentação do projeto
```

---

## 🚀 Como Usar no Google Colab

No notebook do Google Colab, execute em uma célula para instalar o pacote diretamente a partir do repositório no GitHub:

```python
!pip install git+https://github.com/Brunonaive03/mcp-course-secomp.git
```

Em seguida, importe e execute a função `prepare_enviorement`:

```python
from mcp_utils import prepare_enviorement

prepare_enviorement()
```

*(Opcional: você também pode passar explicitamente a URL do repositório como argumento: `prepare_enviorement("https://github.com/Brunonaive03/mcp-course-secomp.git")`)*

---

## ⚙️ O que a função `prepare_enviorement` faz

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
  * `tracks`

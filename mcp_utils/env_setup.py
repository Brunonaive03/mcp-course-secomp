import os
import shutil
import subprocess
import time


def _run_cmd(cmd: str, desc: str, error_msg: str) -> bool:
    print(desc)
    result = subprocess.run(
        cmd,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"⚠️ {error_msg}")
        if result.stderr:
            error_preview = result.stderr.strip()
            print(f"   Detalhes: {error_preview}")
        return False
    return True


def prepare_enviorement(repo_url: str):
    """
    Prepara o ambiente do Google Colab para o mini-curso MCP:
    1. Instala a chave GPG do MongoDB 7.0.
    2. Adiciona o repositório oficial do MongoDB ao sources.list.d.
    3. Roda apt-get update e instala mongodb-org e mongodb-database-tools.
    4. Cria o diretório /data/db e inicia o mongod em background com --fork.
    5. Faz o git clone do repositório (repo_url) para baixar a pasta /data.
    6. Executa o mongorestore para popular o banco de dados 'mcp_music_lab'.
    """
    print("=" * 60)
    print("Iniciando configuração do ambiente MongoDB no Colab...")
    print("=" * 60)

    # 1. Chave GPG do MongoDB 7.0
    gpg_cmd = (
        "curl -fsSL https://www.pgp.mongodb.org/static/pgp/server-7.0.asc | "
        "gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor --yes"
    )
    _run_cmd(
        gpg_cmd,
        "[1/6] Instalando chave GPG do MongoDB 7.0...",
        "Falha ao instalar chave GPG do MongoDB.",
    )

    # 2. Repositório MongoDB 7.0
    repo_cmd = (
        'echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] '
        'https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs 2>/dev/null || echo jammy)/mongodb-org/7.0 multiverse" '
        "| tee /etc/apt/sources.list.d/mongodb-org-7.0.list"
    )
    _run_cmd(
        repo_cmd,
        "[2/6] Adicionando repositório do MongoDB ao sources.list.d...",
        "Falha ao adicionar repositório do MongoDB.",
    )

    # 3. apt-get update e instalação do mongodb-org e ferramentas
    apt_cmd = (
        "DEBIAN_FRONTEND=noninteractive apt-get update -qq && "
        "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq mongodb-org mongodb-database-tools"
    )
    _run_cmd(
        apt_cmd,
        "[3/6] Atualizando pacotes e instalando MongoDB 7.0...",
        "Falha ao instalar pacotes do MongoDB.",
    )

    # 4. Criação do diretório /data/db e inicialização do mongod com --fork
    mongod_cmd = (
        "mkdir -p /data/db /var/log/mongodb && "
        "(pgrep -x mongod > /dev/null || mongod --fork --logpath /var/log/mongodb/mongod.log --dbpath /data/db)"
    )
    _run_cmd(
        mongod_cmd,
        "⚙️[4/6] Criando diretório /data/db e iniciando mongod em background...",
        "Falha ao inicializar o mongod.",
    )

    # Breve pausa para garantir que o daemon esteja pronto para conexões
    time.sleep(2)

    # 5. Git clone do repositório para baixar a pasta /data
    temp_clone_dir = "/tmp/mcp_curso_repo"
    if os.path.exists(temp_clone_dir):
        shutil.rmtree(temp_clone_dir, ignore_errors=True)

    git_clone_cmd = f"git clone {repo_url} {temp_clone_dir}"
    _run_cmd(
        git_clone_cmd,
        f"[5/6] Baixando dados do repositório ({repo_url})...",
        f"Falha ao clonar o repositório {repo_url}.",
    )

    # Determinar caminho da pasta data
    data_dir = os.path.join(temp_clone_dir, "data")
    if not os.path.exists(data_dir):
        # Fallback se data estiver no diretório de trabalho atual
        if os.path.exists("data"):
            data_dir = "data"
        elif os.path.exists(temp_clone_dir):
            data_dir = temp_clone_dir

    # 6. mongorestore no banco mcp_music_lab
    restore_cmd = f"mongorestore --db=mcp_music_lab --drop {data_dir}"
    restore_success = _run_cmd(
        restore_cmd,
        "[6/6] Restaurando banco 'mcp_music_lab' via mongorestore...",
        "Falha ao executar mongorestore.",
    )

    print("=" * 60)
    if restore_success:
        print("Ambiente configurado com sucesso! O MongoDB está pronto para uso.")
        print("Banco: mcp_music_lab | Coleções: albums, reviews, tracks")
    else:
        print("Configuração concluída com possíveis avisos. Verifique os logs acima.")
    print("=" * 60)

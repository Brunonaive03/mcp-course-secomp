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


def _get_system_info():
    """Detecta a distribuição Ubuntu para selecionar a versão compatível do MongoDB."""
    try:
        res = subprocess.run("lsb_release -cs", shell=True, capture_output=True, text=True)
        codename = res.stdout.strip().lower()
    except Exception:
        codename = ""

    if not codename:
        codename = "noble"

    # Ubuntu 24.04 (noble) utiliza MongoDB 8.0 (7.0 não possui pacotes para noble)
    # Ubuntu 22.04 (jammy) e 20.04 (focal) utilizam MongoDB 7.0
    if codename == "noble":
        mongo_version = "8.0"
        gpg_url = "https://pgp.mongodb.com/server-8.0.asc"
    else:
        codename = "jammy" if codename not in ["focal", "jammy"] else codename
        mongo_version = "7.0"
        gpg_url = "https://pgp.mongodb.com/server-7.0.asc"

    return codename, mongo_version, gpg_url


def prepare_environment(repo_url: str = "https://github.com/Brunonaive03/mcp-course-secomp.git"):
    """
    Prepara o ambiente do Google Colab para o mini-curso MCP:
    1. Instala a chave GPG oficial do MongoDB.
    2. Adiciona o repositório oficial do MongoDB ao sources.list.d.
    3. Roda apt-get update e instala mongodb-org e mongodb-database-tools.
    4. Cria o diretório /data/db e inicia o mongod em background com --fork.
    5. Faz o git clone do repositório para baixar a pasta /data.
    6. Executa o mongorestore para popular o banco de dados 'mcp_music_lab'.
    """
    print("=" * 60)
    print("Iniciando configuração do ambiente MongoDB no Colab...")
    print("=" * 60)

    codename, mongo_version, gpg_url = _get_system_info()

    # 1. Chave GPG oficial do MongoDB
    keyring_path = f"/usr/share/keyrings/mongodb-server-{mongo_version}.gpg"
    gpg_cmd = (
        f"curl -fsSL {gpg_url} | "
        f"gpg -o {keyring_path} --dearmor --yes"
    )
    _run_cmd(
        gpg_cmd,
        f"[1/6] Instalando chave GPG do MongoDB {mongo_version}...",
        "Falha ao instalar chave GPG do MongoDB.",
    )

    # 2. Repositório oficial do MongoDB
    repo_cmd = (
        f'echo "deb [ arch=amd64,arm64 signed-by={keyring_path} ] '
        f'https://repo.mongodb.org/apt/ubuntu {codename}/mongodb-org/{mongo_version} multiverse" '
        f"| tee /etc/apt/sources.list.d/mongodb-org-{mongo_version}.list"
    )
    _run_cmd(
        repo_cmd,
        f"[2/6] Adicionando repositório do MongoDB {mongo_version} ({codename}) ao sources.list.d...",
        "Falha ao adicionar repositório do MongoDB.",
    )

    # 3. apt-get update e instalação do mongodb-org e ferramentas
    apt_cmd = (
        "DEBIAN_FRONTEND=noninteractive apt-get update -qq && "
        "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq mongodb-org mongodb-database-tools"
    )
    _run_cmd(
        apt_cmd,
        f"[3/6] Atualizando pacotes e instalando MongoDB {mongo_version}...",
        "Falha ao instalar pacotes do MongoDB.",
    )

    # 4. Criação do diretório /data/db e inicialização do mongod com --fork
    mongod_cmd = (
        "mkdir -p /data/db /var/log/mongodb && "
        "(pgrep -x mongod > /dev/null || mongod --fork --logpath /var/log/mongodb/mongod.log --dbpath /data/db)"
    )
    _run_cmd(
        mongod_cmd,
        "[4/6] Criando diretório /data/db e iniciando mongod em background...",
        "Falha ao inicializar o mongod.",
    )

    # Breve pausa para garantir que o daemon esteja pronto para conexões
    time.sleep(2)

    # 5. Git clone do repositório para baixar a pasta /data
    temp_clone_dir = "/tmp/mcp_curso_repo"
    if os.path.exists(temp_clone_dir):
        shutil.rmtree(temp_clone_dir, ignore_errors=True)

    git_clone_cmd = f"GIT_TERMINAL_PROMPT=0 git clone {repo_url} {temp_clone_dir}"
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


def ensure_mongodb_running() -> bool:
    """
    Verifica se o MongoDB está respondendo na porta 27017.
    Se não estiver ativo mas o pacote já estiver instalado no sistema, tenta iniciá-lo automaticamente.
    """
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=800)
        client.admin.command('ping')
        return True
    except Exception:
        pass

    # Se o executável mongod existir, tenta iniciar em background
    if shutil.which("mongod"):
        print("🔄 [Auto-Start] Detectado 'mongod' instalado mas inativo. Iniciando serviço em background...", flush=True)
        subprocess.run(
            "mkdir -p /data/db /var/log/mongodb && mongod --fork --logpath /var/log/mongodb/mongod.log --dbpath /data/db",
            shell=True,
            check=False,
            capture_output=True,
        )
        time.sleep(2)
        try:
            from pymongo import MongoClient
            client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=1000)
            client.admin.command('ping')
            print("✅ [Auto-Start] Daemon mongod iniciado com sucesso na porta 27017!", flush=True)
            return True
        except Exception:
            pass

    return False



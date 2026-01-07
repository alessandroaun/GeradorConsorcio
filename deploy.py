import os
import re
import json
import subprocess
import shutil
from supabase import create_client, Client

# --- CONFIGURAÇÕES (EDITE AQUI) ---

# 1. Configurações do Supabase
SUPABASE_URL = "https://nhnejoanmggvinnfphir.supabase.co/"
# IMPORTANTE: Use a chave 'service_role' (secret)
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5obmVqb2FubWdndmlubmZwaGlyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NjA3NDk5NCwiZXhwIjoyMDgxNjUwOTk0fQ._QXfa-v4YBC_-xazB4A6LrWeB-oxXiIFfboiqbNQh7Q" 
BUCKET_NAME = "upadates"
FOLDER_PATH = "updates" # Pasta dentro do bucket

# 2. Caminhos Locais
FILE_UPDATER = "updater.py"
FILE_ISS = "inno_gerenciador.iss" # Nome do seu arquivo do Inno Setup 
PATH_OUTPUT_INSTALLER = "Output_Instalador" 

# 3. Caminho do Compilador Inno Setup 
# (Verifique se o caminho está correto no seu PC)
ISCC_PATH = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

def atualizar_versao_arquivo_python(nova_versao):
    print(f"1. Atualizando {FILE_UPDATER}...")
    with open(FILE_UPDATER, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = re.sub(
        r'CURRENT_VERSION = "[0-9.]+"', 
        f'CURRENT_VERSION = "{nova_versao}"', 
        content
    )
    
    with open(FILE_UPDATER, 'w', encoding='utf-8') as f:
        f.write(new_content)

def atualizar_versao_iss(nova_versao):
    print(f"2. Atualizando {FILE_ISS}...")
    with open(FILE_ISS, 'r', encoding='latin-1') as f:
        content = f.read()
    
    new_content = re.sub(
        r'#define MyAppVersion "[0-9.]+"', 
        f'#define MyAppVersion "{nova_versao}"', 
        content
    )
    
    with open(FILE_ISS, 'w', encoding='latin-1') as f:
        f.write(new_content)

def rodar_pyinstaller():
    print("3. Gerando executável (PyInstaller)...")
    # Ajuste os argumentos conforme seu projeto (ícones, pastas adicionais, etc)
    cmd = [
        "pyinstaller", 
        "--onefile", 
        "--noconsole", 
        "--clean", 
        "--name=GerenciadorSimuladorRecon", 
        "--icon=logo_recon-consorcio.ico",
        "app.py"
    ]
    subprocess.run(cmd, check=True)

def rodar_inno_setup():
    print("4. Criando Instalador (Inno Setup)...")
    if not os.path.exists(ISCC_PATH):
        raise Exception(f"Compilador Inno Setup não encontrado em: {ISCC_PATH}")
    
    subprocess.run([ISCC_PATH, FILE_ISS], check=True)

def upload_supabase(nova_versao, changelog):
    print("5. Gerenciando Nuvem (Supabase)...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # --- NOVO: LIMPEZA DE VERSÕES ANTIGAS ---
    print("   -> Verificando arquivos antigos...")
    try:
        # Lista arquivos na pasta 'updates'
        files_in_bucket = supabase.storage.from_(BUCKET_NAME).list(FOLDER_PATH)
        
        files_to_delete = []
        for file in files_in_bucket:
            name = file.get('name', '')
            # Se for um instalador (Setup_*.exe) e NÃO for o version.json
            if name.startswith("Setup_") and name.endswith(".exe"):
                full_path = f"{FOLDER_PATH}/{name}"
                files_to_delete.append(full_path)
        
        if files_to_delete:
            print(f"   -> Removendo {len(files_to_delete)} instalador(es) antigo(s)...")
            supabase.storage.from_(BUCKET_NAME).remove(files_to_delete)
        else:
            print("   -> Nenhum arquivo antigo para limpar.")
            
    except Exception as e:
        print(f"   ⚠️ Aviso: Erro ao tentar limpar arquivos antigos: {e}")
        print("      Continuando com o upload...")
    # ----------------------------------------

    # Nome do arquivo instalador gerado localmente
    installer_name = f"Setup_GerenciadorSimuladorRecon_v{nova_versao}.exe"
    local_installer_path = os.path.join(PATH_OUTPUT_INSTALLER, installer_name)
    
    if not os.path.exists(local_installer_path):
        raise Exception(f"Instalador não encontrado em: {local_installer_path}")

    # A. Upload do Novo Instalador
    print(f"   -> Uploading {installer_name}...")
    remote_path_exe = f"{FOLDER_PATH}/{installer_name}"
    
    with open(local_installer_path, 'rb') as f:
        supabase.storage.from_(BUCKET_NAME).upload(
            path=remote_path_exe, 
            file=f, 
            file_options={"upsert": "true"}
        )

    # Pegar URL Pública
    public_url_exe = supabase.storage.from_(BUCKET_NAME).get_public_url(remote_path_exe)
    
    # B. Atualizar version.json
    print("   -> Atualizando version.json...")
    json_data = {
        "version": nova_versao,
        "url": public_url_exe,
        "changelog": changelog
    }
    
    with open("version.json", "w", encoding='utf-8') as f:
        json.dump(json_data, f, indent=4)
        
    with open("version.json", "rb") as f:
        supabase.storage.from_(BUCKET_NAME).upload(
            path=f"{FOLDER_PATH}/version.json", 
            file=f,
            file_options={"upsert": "true"}
        )
    
    os.remove("version.json")
    print("✅ DEPLOY E LIMPEZA CONCLUÍDOS!")

def main():
    print("=== AUTOMATIZADOR DE DEPLOY v2 (AUTO-CLEAN) ===")
    nova_versao = input("Digite a NOVA versão (ex: 1.0.2): ").strip()
    if not nova_versao: return

    changelog = input("Digite o Changelog (O que mudou?): ").strip()
    if not changelog: changelog = "Melhorias gerais."

    if input(f"Confirmar deploy da v{nova_versao}? (S/N): ").upper() != 'S':
        print("Cancelado.")
        return

    try:
        atualizar_versao_arquivo_python(nova_versao)
        atualizar_versao_iss(nova_versao)
        rodar_pyinstaller()
        rodar_inno_setup()
        upload_supabase(nova_versao, changelog)
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")

if __name__ == "__main__":
    main()
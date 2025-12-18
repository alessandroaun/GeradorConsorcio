# json_utils.py
import json
import os

CONFIG_FILE = "config.json"

def carregar_json(caminho_arquivo):
    if not os.path.exists(caminho_arquivo):
        return {}
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def salvar_json(caminho_arquivo, chave_tabela, novos_dados, substituir=False, metadata_item=None):
    """
    Salva os dados da tabela e, opcionalmente, atualiza os metadados.
    """
    dados_existentes = {}
    
    # Se não for substituir tudo, carrega o existente
    if not substituir:
        dados_existentes = carregar_json(caminho_arquivo)
    
    # 1. Salva/Atualiza os dados da tabela (lista de simulações)
    dados_existentes[chave_tabela] = novos_dados
    
    # 2. Lógica de Metadados (apenas se fornecido)
    if metadata_item:
        # Garante que a chave 'metadata' existe e é uma lista
        if "metadata" not in dados_existentes or not isinstance(dados_existentes["metadata"], list):
            dados_existentes["metadata"] = []
        
        lista_meta = dados_existentes["metadata"]
        id_alvo = metadata_item["id"]
        
        # Procura se já existe esse ID para sobrescrever
        encontrado = False
        for i, item in enumerate(lista_meta):
            if item.get("id") == id_alvo:
                lista_meta[i] = metadata_item # Sobrescreve
                encontrado = True
                break
        
        # Se não encontrou, adiciona no final
        if not encontrado:
            lista_meta.append(metadata_item)
            
        dados_existentes["metadata"] = lista_meta
    
    # Gravação no disco
    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados_existentes, f, indent=4, ensure_ascii=False)

# --- Funções de Persistência de Configuração (App) ---

def salvar_config(dados):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar config: {e}")

def carregar_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None
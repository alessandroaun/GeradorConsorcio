# json_utils.py
import json
import os

CONFIG_FILE = "config.json"
ESTATISTICAS_FILE = "estatisticas_grupos.json" # Arquivo fixo solicitado

def carregar_json(caminho_arquivo):
    if not os.path.exists(caminho_arquivo):
        return {} if "estatisticas" not in caminho_arquivo else [] # Retorna lista para estatisticas
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {} if "estatisticas" not in caminho_arquivo else []

def salvar_json(caminho_arquivo, chave_tabela, novos_dados, substituir=False, metadata_item=None):
    # (Mantenha o código existente desta função aqui...)
    # ... código anterior ...
    # Se você apagou, me avise que mando de novo, mas a ideia é só adicionar a nova função abaixo:
    pass 

# --- NOVA FUNÇÃO PARA O PDF ---
def atualizar_estatisticas_json(novos_dados_lista):
    """
    Lê o arquivo estatisticas_grupos.json.
    Atualiza grupos existentes (substitui) e adiciona novos (append).
    """
    if not novos_dados_lista:
        return

    # 1. Carregar dados existentes
    dados_existentes = []
    if os.path.exists(ESTATISTICAS_FILE):
        try:
            with open(ESTATISTICAS_FILE, 'r', encoding='utf-8') as f:
                dados_existentes = json.load(f)
                if not isinstance(dados_existentes, list):
                    dados_existentes = []
        except:
            dados_existentes = []

    # 2. Criar Mapa para Atualização Rápida (Dict key=Grupo)
    mapa_grupos = {item['Grupo']: item for item in dados_existentes}

    # 3. Atualizar ou Inserir
    count_novos = 0
    count_atualizados = 0

    for novo_item in novos_dados_lista:
        grupo_id = novo_item['Grupo']
        if grupo_id in mapa_grupos:
            mapa_grupos[grupo_id] = novo_item # Substitui
            count_atualizados += 1
        else:
            mapa_grupos[grupo_id] = novo_item # Adiciona
            count_novos += 1

    # 4. Converter de volta para lista e ordenar
    lista_final = list(mapa_grupos.values())
    # Opcional: Ordenar por número do grupo
    lista_final.sort(key=lambda x: x['Grupo'])

    # 5. Salvar
    with open(ESTATISTICAS_FILE, 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, indent=4, ensure_ascii=False)
    
    return count_novos, count_atualizados

# --- Funções de Configuração (Mantenha as existentes) ---
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
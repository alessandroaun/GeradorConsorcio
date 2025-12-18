import json
import os

CONFIG_FILE = "config.json"
ESTATISTICAS_FILE = "estatisticas_grupos.json"

def carregar_json(caminho_arquivo):
    if not os.path.exists(caminho_arquivo):
        return {} if "estatisticas" not in caminho_arquivo else [] 
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {} if "estatisticas" not in caminho_arquivo else []

def salvar_json(caminho_arquivo, chave_tabela, novos_dados, substituir=False, metadata_item=None):
    """
    Salva ou atualiza uma tabela dentro do arquivo JSON estruturado.
    Estrutura: { "metadata": [], "data": { "chave": [...] } }
    """
    # Estrutura base padrão
    arquivo_dados = {"metadata": [], "data": {}}

    # 1. Se o arquivo existe e NÃO é para substituir (criar novo do zero), carrega o atual
    if os.path.exists(caminho_arquivo) and not substituir:
        try:
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                conteudo_existente = json.load(f)
                # Garante a estrutura correta caso o arquivo esteja incompleto
                if "metadata" in conteudo_existente:
                    arquivo_dados["metadata"] = conteudo_existente["metadata"]
                if "data" in conteudo_existente:
                    arquivo_dados["data"] = conteudo_existente["data"]
        except (json.JSONDecodeError, Exception):
            # Se der erro ao ler, assume arquivo corrompido e cria novo, 
            # ou você pode optar por não fazer nada. Aqui assumimos 'reset' em caso de erro.
            pass

    # 2. Atualiza os DADOS da tabela específica
    arquivo_dados["data"][chave_tabela] = novos_dados

    # 3. Atualiza os METADADOS (se fornecido)
    if metadata_item:
        # Verifica se já existe um metadata com esse ID para atualizar
        id_meta = metadata_item.get("id")
        encontrado = False
        
        for i, item in enumerate(arquivo_dados["metadata"]):
            if item.get("id") == id_meta:
                arquivo_dados["metadata"][i] = metadata_item # Substitui o metadata antigo
                encontrado = True
                break
        
        if not encontrado:
            arquivo_dados["metadata"].append(metadata_item) # Adiciona novo

    # 4. Escreve no disco
    try:
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(arquivo_dados, f, indent=4, ensure_ascii=False)
    except Exception as e:
        raise Exception(f"Erro ao escrever no arquivo: {str(e)}")

# --- FUNÇÃO PARA O PDF ---
def atualizar_estatisticas_json(novos_dados_lista):
    """
    Lê o arquivo estatisticas_grupos.json.
    Atualiza grupos existentes (substitui) e adiciona novos (append).
    """
    if not novos_dados_lista:
        return 0, 0

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
    mapa_grupos = {str(item.get('Grupo')): item for item in dados_existentes}

    # 3. Atualizar ou Inserir
    count_novos = 0
    count_atualizados = 0

    for novo_item in novos_dados_lista:
        grupo_id = str(novo_item.get('Grupo'))
        
        if grupo_id in mapa_grupos:
            mapa_grupos[grupo_id] = novo_item # Substitui
            count_atualizados += 1
        else:
            mapa_grupos[grupo_id] = novo_item # Adiciona
            count_novos += 1

    # 4. Converter de volta para lista e ordenar
    lista_final = list(mapa_grupos.values())
    
    # Tenta ordenar por número de grupo (se possível)
    try:
        lista_final.sort(key=lambda x: int(x.get('Grupo', 0)))
    except:
        pass

    # 5. Salvar
    with open(ESTATISTICAS_FILE, 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, indent=4, ensure_ascii=False)
    
    return count_novos, count_atualizados

# --- Funções de Configuração ---
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
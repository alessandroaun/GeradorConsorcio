import json
import os
from supabase import create_client, Client

# --- CONFIGURAÇÃO DO SUPABASE ---
# Substitua pelos seus dados reais do painel do Supabase
SUPABASE_URL = "https://nhnejoanmggvinnfphir.supabase.co/" 
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5obmVqb2FubWdndmlubmZwaGlyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NjA3NDk5NCwiZXhwIjoyMDgxNjUwOTk0fQ._QXfa-v4YBC_-xazB4A6LrWeB-oxXiIFfboiqbNQh7Q" 
BUCKET_NAME = "consorciorecon-json"

# Nomes dos Arquivos na Nuvem
FILE_DADOS = "dados_consorcio.json"
FILE_ESTATISTICAS = "estatisticas_grupos.json"
FILE_RELACAO = "relacao_grupos.json"
FILE_HISTORICO = "historico_assembleias.json" # <--- NOVO ARQUIVO

# Inicializa Cliente (Singleton simples)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNÇÕES DE ARMAZENAMENTO (STORAGE) ---

def download_json_supabase(filename):
    """Baixa o JSON do Supabase e converte para dicionário/lista Python."""
    try:
        # Baixa os bytes do arquivo
        data_bytes = supabase.storage.from_(BUCKET_NAME).download(filename)
        # Decodifica e carrega JSON
        return json.loads(data_bytes.decode('utf-8'))
    except Exception as e:
        print(f"Erro ao baixar {filename}: {e}")
        # Se falhar (arquivo não existe), retorna estrutura vazia baseada no tipo
        if filename == FILE_ESTATISTICAS: return []
        if filename == FILE_RELACAO: return []
        if filename == FILE_HISTORICO: return [] # <--- Tratamento para o novo arquivo
        return {"metadata": [], "data": {}}

def upload_json_supabase(filename, data):
    """Converte dados Python para JSON e faz Upload (Sobrescreve) no Supabase."""
    try:
        json_str = json.dumps(data, indent=4, ensure_ascii=False)
        # O parâmetro upsert=True garante que sobrescreva o existente
        supabase.storage.from_(BUCKET_NAME).upload(
            path=filename, 
            file=json_str.encode('utf-8'), 
            file_options={"content-type": "application/json", "upsert": "true"}
        )
        return True
    except Exception as e:
        raise Exception(f"Erro ao enviar para Supabase: {e}")

# --- FUNÇÕES DE LÓGICA DE NEGÓCIO (ADAPTADAS) ---

def carregar_dados_tabelas():
    """Wrapper específico para carregar o dados_consorcio.json"""
    return download_json_supabase(FILE_DADOS)

def salvar_dados_tabelas(chave_tabela, novos_dados, metadata_item=None):
    """
    1. Baixa o dados_consorcio.json atual da nuvem.
    2. Atualiza os dados locais.
    3. Envia de volta para a nuvem.
    """
    # 1. Baixar Estado Atual
    arquivo_dados = download_json_supabase(FILE_DADOS)
    
    # Garante estrutura básica se estiver vazio
    if "metadata" not in arquivo_dados: arquivo_dados["metadata"] = []
    if "data" not in arquivo_dados: arquivo_dados["data"] = {}

    # 2. Atualiza os DADOS da tabela específica
    arquivo_dados["data"][chave_tabela] = novos_dados

    # 3. Atualiza os METADADOS (se fornecido)
    if metadata_item:
        id_meta = metadata_item.get("id")
        encontrado = False
        for i, item in enumerate(arquivo_dados["metadata"]):
            if item.get("id") == id_meta:
                arquivo_dados["metadata"][i] = metadata_item
                encontrado = True
                break
        if not encontrado:
            arquivo_dados["metadata"].append(metadata_item)

    # 4. Upload
    upload_json_supabase(FILE_DADOS, arquivo_dados)

def atualizar_estatisticas_json(novos_dados_lista):
    """
    Lê estatisticas_grupos.json da nuvem, mescla (sobrescreve pelo Grupo ID) e salva.
    """
    if not novos_dados_lista: return 0, 0

    # 1. Baixar
    dados_existentes = download_json_supabase(FILE_ESTATISTICAS)
    if not isinstance(dados_existentes, list): dados_existentes = []

    mapa_grupos = {str(item.get('Grupo')): item for item in dados_existentes}

    count_novos = 0
    count_atualizados = 0

    # 2. Mesclar
    for novo_item in novos_dados_lista:
        grupo_id = str(novo_item.get('Grupo'))
        if grupo_id in mapa_grupos:
            mapa_grupos[grupo_id] = novo_item
            count_atualizados += 1
        else:
            mapa_grupos[grupo_id] = novo_item
            count_novos += 1

    lista_final = list(mapa_grupos.values())
    try: lista_final.sort(key=lambda x: int(x.get('Grupo', 0)))
    except: pass

    # 3. Upload
    upload_json_supabase(FILE_ESTATISTICAS, lista_final)
    
    return count_novos, count_atualizados

def atualizar_historico_assembleias(novos_dados_pdf):
    """
    NOVA FUNÇÃO:
    Baixa o histórico, adiciona novos registros verificando duplicidade
    (Chave única: Grupo + Assembleia) e sobe novamente.
    Permite múltiplos registros do mesmo grupo, desde que em assembleias diferentes.
    """
    if not novos_dados_pdf: return 0, 0

    # 1. Baixar histórico atual
    historico_atual = download_json_supabase(FILE_HISTORICO)
    if not isinstance(historico_atual, list):
        historico_atual = []

    registros_adicionados = 0
    registros_atualizados = 0

    # 2. Processar cada item extraído do PDF
    for novo_item in novos_dados_pdf:
        grupo_novo = str(novo_item.get('Grupo', '')).strip()
        assembleia_nova = str(novo_item.get('Assembleia', '')).strip() # Data ou ID da assembleia

        if not grupo_novo or not assembleia_nova:
            continue # Pula se não tiver dados identificadores

        encontrado = False
        
        # Procura se já existe esse Grupo naquela Assembleia específica
        for i, item_hist in enumerate(historico_atual):
            grupo_hist = str(item_hist.get('Grupo', '')).strip()
            assembleia_hist = str(item_hist.get('Assembleia', '')).strip()

            if grupo_hist == grupo_novo and assembleia_hist == assembleia_nova:
                # JÁ EXISTE: Atualiza os dados (caso tenha mudado algo na leitura)
                historico_atual[i] = novo_item
                registros_atualizados += 1
                encontrado = True
                break
        
        if not encontrado:
            # NÃO EXISTE: Adiciona ao histórico (Append)
            historico_atual.append(novo_item)
            registros_adicionados += 1

    # 3. Ordenar (Por Grupo e depois por Assembleia)
    try:
        historico_atual.sort(key=lambda x: (int(x.get('Grupo', 0)), x.get('Assembleia', '')))
    except:
        pass

    # 4. Upload de volta para o Supabase
    upload_json_supabase(FILE_HISTORICO, historico_atual)
    
    return registros_adicionados, registros_atualizados

# --- CONFIG LOCAL (Mantido localmente pois é config do APP, não dado do sistema) ---
CONFIG_FILE = "config.json"
def salvar_config(dados):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4)
    except: pass

def carregar_config():
    if not os.path.exists(CONFIG_FILE): return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return None
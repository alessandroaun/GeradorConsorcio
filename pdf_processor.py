# pdf_processor.py
import pdfplumber
import re
import os

def extrair_dados_pdf(pdf_path, callback_log=None):
    """
    Processa o PDF e retorna uma lista de dicionários com os dados dos grupos.
    callback_log: função opcional para enviar logs para a UI (ex: print visual).
    """
    def log(msg):
        if callback_log:
            callback_log(msg)
        else:
            print(msg)

    log(f"🚀 Iniciando processamento do arquivo: {os.path.basename(pdf_path)}...")

    if not os.path.exists(pdf_path):
        log(f"❌ Erro: Arquivo não encontrado.")
        return []

    grupos_data = []
    grupos_processados_set = set()
    
    # Estado
    grupo_atual = None
    dados_grupo = None
    ultimo_percentual = 0.0
    
    # Data Global
    data_assembleia_global = "-"
    encontrou_data_global = False

    # Regex
    re_grupo = re.compile(r'(?:Grupo\s+(\d{4}))|(\d{4})\s+Grupo|^Grupo$', re.IGNORECASE)
    re_numero_isolado = re.compile(r'^(\d{4})$')
    re_percentual = re.compile(r'(\d{1,3},\d{4,})')
    re_tipo = re.compile(r'(Livre|Fixo|Sorteio)', re.IGNORECASE)
    re_cotas_grupo = re.compile(r'Cotas\s*Grupo\s*[:.]?\s*(\d+)', re.IGNORECASE)
    re_data_header = re.compile(r'Contempla[çc][ãa]o\s*de[:\s]*(\d{2}/\d{2}/\d{2,4})', re.IGNORECASE)

    esperando_numero_grupo = False

    def novo_estrutura_grupo():
        return {
            'qtdContempladosManual': 0,
            'qtdContempladosOficial': None,
            'qtdLanceFixo': 0,
            'qtdLanceLivre': 0,
            'lancesLivresValues': []
        }

    def processar_e_salvar_grupo_atual(num_grupo, dados):
        lances = dados['lancesLivresValues']
        media = sum(lances) / len(lances) if lances else 0.0
        menor = min(lances) if lances else 0.0
        
        # Lógica de negócio: Fixo - 1 (mínimo 0)
        lances_fixos_ajustados = max(0, dados['qtdLanceFixo'] - 1)

        qtd_final = dados['qtdContempladosOficial'] if dados['qtdContempladosOficial'] is not None else dados['qtdContempladosManual']

        try:
            obj = {
                "Grupo": int(num_grupo),
                "Assembleia": "-", # Será preenchido no final
                "Qtd Contemplados": qtd_final,
                "Qtd Lance Fixo (30/45)": lances_fixos_ajustados,
                "Qtd Lance Livre": dados['qtdLanceLivre'],
                "Media Lance Livre": round(media, 4),
                "Menor Lance Livre": round(menor, 4)
            }
            grupos_data.append(obj)
            log(f"   -> Grupo {num_grupo} processado (Contemplados: {qtd_final})")
        except ValueError:
            pass

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_paginas = len(pdf.pages)
            log(f"📄 O documento possui {total_paginas} páginas.")

            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text: continue

                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line: continue

                    # 1. Data Global
                    if not encontrou_data_global:
                        match_dt = re_data_header.search(line)
                        if match_dt:
                            data_assembleia_global = match_dt.group(1)
                            encontrou_data_global = True
                            log(f"📅 Data da Assembleia detectada: {data_assembleia_global}")

                    # 2. Cotas Oficial
                    match_cotas = re_cotas_grupo.search(line)
                    if match_cotas and dados_grupo:
                        dados_grupo['qtdContempladosOficial'] = int(match_cotas.group(1))

                    # 3. Mudança de Grupo
                    match_grupo = re_grupo.search(line)
                    match_num_isolado = re_numero_isolado.search(line)
                    novo_numero = None

                    if match_grupo:
                        if match_grupo.group(1) or match_grupo.group(2):
                            novo_numero = match_grupo.group(1) or match_grupo.group(2)
                        elif line.lower() == 'grupo':
                            esperando_numero_grupo = True
                            continue
                    elif esperando_numero_grupo and match_num_isolado:
                        novo_numero = match_num_isolado.group(1)
                        esperando_numero_grupo = False

                    if novo_numero:
                        # Salva o anterior
                        if grupo_atual and dados_grupo:
                            processar_e_salvar_grupo_atual(grupo_atual, dados_grupo)
                        
                        try:
                            novo_num_int = int(novo_numero)
                            if novo_num_int in grupos_processados_set:
                                # Duplicado no mesmo PDF, reseta para ignorar lances
                                grupo_atual = novo_numero
                                dados_grupo = None 
                            else:
                                grupos_processados_set.add(novo_num_int)
                                grupo_atual = novo_numero
                                dados_grupo = novo_estrutura_grupo()
                                ultimo_percentual = 0.0
                        except:
                            grupo_atual = novo_numero
                            dados_grupo = novo_estrutura_grupo()
                        continue

                    # 4. Lances
                    if grupo_atual and dados_grupo:
                        # Percentual
                        match_perc = re_percentual.search(line)
                        percentual_nesta_linha = 0.0
                        if match_perc:
                            try:
                                val = float(match_perc.group(1).replace(',', '.'))
                                if 0 < val <= 100:
                                    ultimo_percentual = val
                                    percentual_nesta_linha = val
                            except: pass

                        # Tipo
                        match_tipo = re_tipo.search(line)
                        if match_tipo:
                            tipo = match_tipo.group(1).lower()
                            dados_grupo['qtdContempladosManual'] += 1
                            
                            percentual_real = percentual_nesta_linha if percentual_nesta_linha > 0 else ultimo_percentual

                            if tipo == 'fixo':
                                dados_grupo['qtdLanceFixo'] += 1
                            elif tipo == 'livre':
                                dados_grupo['qtdLanceLivre'] += 1
                                if percentual_real > 0:
                                    dados_grupo['lancesLivresValues'].append(percentual_real)

            # Salva o último grupo do loop
            if grupo_atual and dados_grupo:
                processar_e_salvar_grupo_atual(grupo_atual, dados_grupo)

            # Aplica Data Global
            if not encontrou_data_global:
                log("⚠️ AVISO: Data 'Contemplação de:' não encontrada. Usando '-'.")
            
            for gp in grupos_data:
                gp['Assembleia'] = data_assembleia_global

            return grupos_data

    except Exception as e:
        log(f"❌ Erro crítico ao ler PDF: {str(e)}")
        return []
# gerador.py
from coeficientes import TAXAS

def calcular_simulacao(grupo, plano_tipo, prazo, credito_inicial, credito_final, passo, custom_data=None):
    """
    Gera a lista de créditos e parcelas com a lógica corrigida:
    - Taxas incidem sobre 100% do crédito.
    - Amortização incide sobre o Fator do Plano (100%, 75% ou 50%).
    - Seguro incide sobre o Saldo Devedor Total (Crédito 100% + Taxas).
    """
    resultados = []
    
    # Garantir que o loop inclua o valor final e use passo inteiro
    for valor_credito in range(int(credito_inicial), int(credito_final) + 1, int(passo)):
        
        # --- 1. Definição das Variáveis (Busca no coeficientes.py ou Custom) ---
        if custom_data:
            # Aba ESPECIAL
            fator_plano = custom_data['fator'] # ex: 0.75
            tx_adm = custom_data['adm']
            tx_fundo = custom_data['fundo']
            tx_seguro = custom_data['seguro']
        else:
            # Abas 2011 e 5121
            dados_grupo = TAXAS[grupo]
            tx_fundo = dados_grupo['fundo_reserva']
            tx_seguro = dados_grupo['seguro']

            if grupo == "2011":
                tx_adm = dados_grupo['adm']
                fator_plano = dados_grupo['planos'][plano_tipo] # 1.0, 0.75 ou 0.50
            
            elif grupo == "5121":
                dados_plano = dados_grupo['planos'][plano_tipo]
                fator_plano = dados_plano['fator']
                tx_adm = dados_plano['adm']

        # --- 2. Cálculo Matemático (Regra Superlight Corrigida) ---

        # A. Cálculo do Montante Total (Crédito + Taxas Totais)
        soma_taxas_pct = tx_adm + tx_fundo
        montante_total = valor_credito * (1 + soma_taxas_pct)

        # B. Cálculo da Parcela SSV
        # Se for Grupo 2011 e Plano Superlight (SL), divide por 2 no final
        if grupo == "2011" and plano_tipo == "SL":
            parcela_ssv = (montante_total / prazo) / 2
        else:
            # Mantém a lógica padrão para os demais planos (Normal/Light)
            # Para o Light (L), a amortização é reduzida no fator_plano lá em cima
            valor_das_taxas = valor_credito * soma_taxas_pct
            valor_amortizacao = valor_credito * fator_plano
            parcela_ssv = (valor_das_taxas + valor_amortizacao) / prazo

        # C. Cálculo do Seguro (Incide sobre o montante total: Crédito + Taxas)
        # Regra: (Crédito + 28%) * 0,059%
        valor_seguro = montante_total * tx_seguro

        # D. Parcela Com Seguro de Vida (CSV)
        parcela_csv = parcela_ssv + valor_seguro

        # --- 3. Montagem do Objeto ---
        item = {
            "credito": valor_credito,
            "prazos": [
                {
                    "prazo": int(prazo),
                    "parcela_CSV": round(parcela_csv, 2),
                    "parcela_SSV": round(parcela_ssv, 2)
                }
            ]
        }
        resultados.append(item)

    return resultados
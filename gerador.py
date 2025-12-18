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

        # --- 2. Cálculo Matemático (Regra Corrigida) ---

        # A. Cálculo das Taxas (Adm + Fundo)
        # Regra: Multiplica-se o crédito (cheio) pela soma da taxa de adm com fundo de reserva
        soma_taxas_pct = tx_adm + tx_fundo
        valor_das_taxas = valor_credito * soma_taxas_pct

        # B. Cálculo da Amortização (Fundo Comum)
        # Regra: ...soma com o valor de X% do crédito (onde X é o fator do plano)
        valor_amortizacao = valor_credito * fator_plano

        # C. Parcela Sem Seguro de Vida (SSV)
        # Regra: (Valor das Taxas + Valor Amortização) / Prazo
        montante_para_parcela = valor_das_taxas + valor_amortizacao
        parcela_ssv = montante_para_parcela / prazo

        # D. Cálculo do Seguro
        # Regra: Soma-se o crédito (cheio) com a taxa de adm e fundo. Do resultado multiplica pelo % do seguro.
        # Obs: Crédito Cheio + Valor das Taxas calculadas acima
        saldo_devedor_total = valor_credito + valor_das_taxas
        valor_seguro = saldo_devedor_total * tx_seguro

        # E. Parcela Com Seguro de Vida (CSV)
        # Regra: Parcela SSV + Valor do Seguro
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
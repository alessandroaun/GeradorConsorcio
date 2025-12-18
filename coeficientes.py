# coeficientes.py

# Taxas em formato decimal (ex: 25% = 0.25)
TAXAS = {
    "2011": {
        "adm": 0.25,          # 25%
        "fundo_reserva": 0.03,# 3%
        "seguro": 0.00059,    # 0.059%
        "planos": {
            "N": 1.0,         # 100%
            "L": 0.75,        # 75%
            "SL": 0.50        # 50%
        }
    },
    "5121": {
        "fundo_reserva": 0.03,# 3%
        "seguro": 0.00084,    # 0.084%
        "planos": {
            "N": {"fator": 1.0, "adm": 0.19},   # 19% Adm
            "L": {"fator": 0.75, "adm": 0.20}   # 20% Adm
        }
    }
}
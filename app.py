# app.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from gerador import calcular_simulacao
from json_utils import salvar_json, salvar_config, carregar_config

class ConsorcioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gerador de Tabelas JSON - Consórcio")
        self.root.geometry("600x750") 
        
        style = ttk.Style()
        style.theme_use('clam')

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, expand=True, fill='both')

        self.tab_2011 = ttk.Frame(self.notebook)
        self.tab_5121 = ttk.Frame(self.notebook)
        self.tab_especial = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_2011, text='  Imóvel 2011  ')
        self.notebook.add(self.tab_5121, text='  Auto 5121  ')
        self.notebook.add(self.tab_especial, text='  ESPECIAL  ')

        # Tenta carregar configuração anterior
        self.last_config = carregar_config()

        # Inicializa Variáveis
        self.vars = {
            '2011': self.init_vars('2011'),
            '5121': self.init_vars('5121'),
            'esp': self.init_vars_especial()
        }

        # Montar Interfaces
        self.setup_tab_padrao(self.tab_2011, "2011", ["Normal (N)", "Light (L)", "SuperLight (SL)"], ["N", "L", "SL"])
        self.setup_tab_padrao(self.tab_5121, "5121", ["Normal (N)", "Light (L)"], ["N", "L"])
        self.setup_tab_especial()

    def init_vars(self, tipo):
        saved = self.last_config.get(tipo, {}) if self.last_config else {}

        if tipo == '2011':
            def_plano = 'N'
            def_prazo = 180
            def_ini = 200000.0
            def_fim = 500000.0
            def_passo = 10000.0
        else: # 5121
            def_plano = 'N'
            def_prazo = 106      
            def_ini = 80000.0    
            def_fim = 110000.0   
            def_passo = 10000.0  

        return {
            'plano': tk.StringVar(value=saved.get('plano', def_plano)),
            'prazo': tk.IntVar(value=saved.get('prazo', def_prazo)),
            'credito_ini': tk.DoubleVar(value=saved.get('credito_ini', def_ini)),
            'credito_fim': tk.DoubleVar(value=saved.get('credito_fim', def_fim)),
            'passo': tk.DoubleVar(value=saved.get('passo', def_passo)),
            'novo_arquivo': tk.BooleanVar(value=saved.get('novo_arquivo', False))
        }

    def init_vars_especial(self):
        saved = self.last_config.get('esp', {}) if self.last_config else {}
        
        return {
            'id_tabela': tk.StringVar(value=saved.get('id_tabela', "custom01")), 
            'nome_real': tk.StringVar(value=saved.get('nome_real', "Minha Tabela Personalizada")), 
            'plano_tipo': tk.StringVar(value=saved.get('plano_tipo', "N")), 
            'adm': tk.DoubleVar(value=saved.get('adm', 25.0)),
            'seguro': tk.DoubleVar(value=saved.get('seguro', 0.059)),
            'prazo': tk.IntVar(value=saved.get('prazo', 180)),
            'credito_ini': tk.DoubleVar(value=saved.get('credito_ini', 200000.0)),
            'credito_fim': tk.DoubleVar(value=saved.get('credito_fim', 500000.0)),
            'passo': tk.DoubleVar(value=saved.get('passo', 10000.0)),
            'novo_arquivo': tk.BooleanVar(value=saved.get('novo_arquivo', False))
        }

    def salvar_estado_atual(self):
        dados_para_salvar = {
            '2011': {k: v.get() for k, v in self.vars['2011'].items()},
            '5121': {k: v.get() for k, v in self.vars['5121'].items()},
            'esp': {k: v.get() for k, v in self.vars['esp'].items()}
        }
        salvar_config(dados_para_salvar)

    def setup_tab_padrao(self, parent, key, radio_labels, radio_values):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill='both', expand=True)

        lbl_frame_plano = ttk.LabelFrame(frame, text="Selecione o Plano", padding=10)
        lbl_frame_plano.pack(fill='x', pady=5)
        
        for text, val in zip(radio_labels, radio_values):
            ttk.Radiobutton(lbl_frame_plano, text=text, variable=self.vars[key]['plano'], value=val).pack(side='left', padx=10)

        self.criar_input(frame, "Prazo (meses):", self.vars[key]['prazo'])
        self.criar_input(frame, "Crédito Inicial (R$):", self.vars[key]['credito_ini'])
        self.criar_input(frame, "Crédito Final (R$):", self.vars[key]['credito_fim'])
        self.criar_input(frame, "Intervalo/Passo (R$):", self.vars[key]['passo'])

        ttk.Checkbutton(frame, text="Criar NOVO arquivo (sobrescreve o anterior)", variable=self.vars[key]['novo_arquivo']).pack(pady=15)
        ttk.Button(frame, text="GERAR JSON", command=lambda: self.gerar_padrao(key)).pack(fill='x', pady=10)

    def setup_tab_especial(self):
        frame = ttk.Frame(self.tab_especial, padding=20)
        frame.pack(fill='both', expand=True)
        key = 'esp'

        self.criar_input(frame, "ID da tabela (sem espaços):", self.vars[key]['id_tabela'])
        self.criar_input(frame, "Nome da Tabela:", self.vars[key]['nome_real'])
        
        lf_plano = ttk.LabelFrame(frame, text="Configuração do Plano (Fator)", padding=10)
        lf_plano.pack(fill='x', pady=5)
        
        opcoes = [("Normal (100%)", "N"), ("Light (75%)", "L"), ("SuperLight (50%)", "SL")]
        for text, val in opcoes:
            ttk.Radiobutton(lf_plano, text=text, variable=self.vars[key]['plano_tipo'], value=val).pack(side='left', padx=10)

        lf_taxas = ttk.LabelFrame(frame, text="Taxas", padding=10)
        lf_taxas.pack(fill='x', pady=5)
        
        self.criar_input(lf_taxas, "Taxa Adm Total (%):", self.vars[key]['adm'])
        self.criar_input(lf_taxas, "Seguro Mensal (%):", self.vars[key]['seguro'])
        ttk.Label(lf_taxas, text="Fundo de Reserva: Fixo em 3%", foreground="gray").pack(pady=2)

        lf_range = ttk.LabelFrame(frame, text="Faixa de Crédito e Prazo", padding=10)
        lf_range.pack(fill='x', pady=5)
        self.criar_input(lf_range, "Prazo:", self.vars[key]['prazo'])
        self.criar_input(lf_range, "Início:", self.vars[key]['credito_ini'])
        self.criar_input(lf_range, "Fim:", self.vars[key]['credito_fim'])
        self.criar_input(lf_range, "Passo:", self.vars[key]['passo'])

        ttk.Checkbutton(frame, text="Criar NOVO arquivo", variable=self.vars[key]['novo_arquivo']).pack(pady=15)
        ttk.Button(frame, text="GERAR TABELA ESPECIAL", command=self.gerar_especial).pack(fill='x', pady=10)

    def criar_input(self, parent, label_text, variable):
        f = ttk.Frame(parent)
        f.pack(fill='x', pady=5)
        ttk.Label(f, text=label_text, width=30).pack(side='left')
        ttk.Entry(f, textvariable=variable).pack(side='right', expand=True, fill='x')

    def get_caminho_salvamento(self, novo_arquivo):
        if novo_arquivo:
            return filedialog.asksaveasfilename(
                title="Salvar Novo Arquivo",
                defaultextension=".json",
                filetypes=[("JSON", "*.json")],
                initialfile="tabelas.json"
            )
        else:
            path = filedialog.askopenfilename(title="Selecionar JSON para Atualizar", filetypes=[("JSON", "*.json")])
            if not path: 
                 return None
            return path

    def gerar_padrao(self, grupo):
        self.salvar_estado_atual() 
        
        dados = self.vars[grupo]
        plano = dados['plano'].get()
        
        tipo = "imovel" if grupo == "2011" else "auto"
        sufixo = "normal" if plano == "N" else plano
        chave_tabela = f"t_{tipo}{grupo}_{sufixo}"

        try:
            resultado = calcular_simulacao(
                grupo, plano, 
                dados['prazo'].get(), 
                dados['credito_ini'].get(), 
                dados['credito_fim'].get(), 
                dados['passo'].get()
            )

            caminho = self.get_caminho_salvamento(dados['novo_arquivo'].get())
            if not caminho: return

            salvar_json(caminho, chave_tabela, resultado, substituir=dados['novo_arquivo'].get())
            messagebox.showinfo("Sucesso", f"Tabela '{chave_tabela}' gerada com sucesso!\nSalvo em: {caminho}")

        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro: {str(e)}")

    def gerar_especial(self):
        self.salvar_estado_atual()

        dados = self.vars['esp']
        id_input = dados['id_tabela'].get().replace(" ", "") 
        nome_real = dados['nome_real'].get()
        plano_selecionado = dados['plano_tipo'].get()

        mapa_fatores = {"N": 1.0, "L": 0.75, "SL": 0.50}
        mapa_sufixos = {"N": "_normal", "L": "_L", "SL": "_SL"}
        mapa_nomes_planos = {"N": "NORMAL", "L": "LIGHT", "SL": "SUPERLIGHT"}

        fator_calculado = mapa_fatores.get(plano_selecionado, 1.0)
        sufixo = mapa_sufixos.get(plano_selecionado, "")
        
        chave_tabela = f"t_{id_input}{sufixo}"

        seguro_pct = dados['seguro'].get()
        
        if abs(seguro_pct - 0.059) < 0.0001:
            categoria = "IMOVEL"
        elif abs(seguro_pct - 0.084) < 0.0001:
            categoria = "AUTO"
        else:
            categoria = "OUTROS"

        custom_data = {
            'fator': fator_calculado,      
            'adm': dados['adm'].get() / 100.0,
            'fundo': 0.03,
            'seguro': seguro_pct / 100.0,
        }

        # Correção aqui: Arredondamento para 5 casas decimais
        seguro_final = round(seguro_pct / 100.0, 5)

        metadata_item = {
            "id": chave_tabela,
            "name": nome_real,
            "category": categoria,
            "plan": mapa_nomes_planos.get(plano_selecionado, "NORMAL"),
            "taxaAdmin": dados['adm'].get() / 100.0,
            "fundoReserva": 0.03,
            "seguroPct": seguro_final, # Valor arredondado
            "maxLanceEmbutido": 0.25
        }

        try:
            resultado = calcular_simulacao(
                "ESPECIAL", "CUSTOM",
                dados['prazo'].get(),
                dados['credito_ini'].get(),
                dados['credito_fim'].get(),
                dados['passo'].get(),
                custom_data=custom_data
            )

            caminho = self.get_caminho_salvamento(dados['novo_arquivo'].get())
            if not caminho: return

            salvar_json(
                caminho, 
                chave_tabela, 
                resultado, 
                substituir=dados['novo_arquivo'].get(),
                metadata_item=metadata_item
            )
            
            messagebox.showinfo("Sucesso", f"Tabela Especial '{chave_tabela}' gerada!\nMetadados atualizados.\nSalvo em: {caminho}")

        except Exception as e:
            messagebox.showerror("Erro", f"Erro na aba especial: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConsorcioApp(root)
    root.mainloop()
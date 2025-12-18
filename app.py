import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading # Para não travar a tela enquanto processa o PDF
import os

from gerador import calcular_simulacao
# Importar a nova função de PDF e JSON Utils
from json_utils import salvar_json, salvar_config, carregar_config, atualizar_estatisticas_json, ESTATISTICAS_FILE
from pdf_processor import extrair_dados_pdf

# --- DESIGN SYSTEM ---
COLOR_BG = "#F9FAFB"
COLOR_CARD = "#FFFFFF"
COLOR_PRIMARY = "#2563EB"
COLOR_TEXT_MAIN = "#111827"
COLOR_TEXT_SUB = "#6B7280"
COLOR_BORDER = "#E5E7EB"
COLOR_SUCCESS = "#059669" # Verde para logs de sucesso

class ConsorcioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gerador JSON & Leitor de Assembleias")
        self.root.geometry("600x650") 
        self.root.configure(bg=COLOR_BG)
        
        self.setup_styles()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)

        self.tab_2011 = ttk.Frame(self.notebook, style="Main.TFrame")
        self.tab_5121 = ttk.Frame(self.notebook, style="Main.TFrame")
        self.tab_especial = ttk.Frame(self.notebook, style="Main.TFrame")
        self.tab_pdf = ttk.Frame(self.notebook, style="Main.TFrame") # NOVA ABA

        self.notebook.add(self.tab_2011, text=' 🏠 2011 ')
        self.notebook.add(self.tab_5121, text=' 🚗 5121 ')
        self.notebook.add(self.tab_especial, text=' ✨ Especial ')
        self.notebook.add(self.tab_pdf, text=' 📄 PDF Resultados ') # NOVA ABA

        self.last_config = carregar_config()

        self.vars = {
            '2011': self.init_vars('2011'),
            '5121': self.init_vars('5121'),
            'esp': self.init_vars_especial(),
            'pdf': {'path': tk.StringVar()} # Var para o PDF
        }

        self.setup_tab_padrao(self.tab_2011, "2011", ["Normal", "Light", "SuperLight"], ["N", "L", "SL"])
        self.setup_tab_padrao(self.tab_5121, "5121", ["Normal", "Light"], ["N", "L"])
        self.setup_tab_especial()
        self.setup_tab_pdf() # Setup nova aba

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam') 

        style.configure("Main.TFrame", background=COLOR_BG)
        style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 8, "bold"), padding=[10, 4])
        
        style.configure("Card.TLabelframe", background=COLOR_BG, bordercolor=COLOR_BORDER, borderwidth=1)
        style.configure("Card.TLabelframe.Label", font=("Segoe UI", 8, "bold"), foreground=COLOR_PRIMARY, background=COLOR_BG)

        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT_MAIN, font=("Segoe UI", 8))
        style.configure("Sub.TLabel", background=COLOR_BG, foreground=COLOR_TEXT_SUB, font=("Segoe UI", 8))
        
        style.configure("TEntry", fieldbackground=COLOR_CARD, bordercolor=COLOR_BORDER, padding=3)
        style.configure("TRadiobutton", background=COLOR_BG, font=("Segoe UI", 8))
        style.configure("TCheckbutton", background=COLOR_BG, font=("Segoe UI", 8))

        style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), background=COLOR_PRIMARY, foreground="white")
        style.map("Action.TButton", background=[("active", "#1D4ED8")])

        # Estilo botão secundário (Selecionar arquivo)
        style.configure("Sec.TButton", font=("Segoe UI", 8), background="#E5E7EB", foreground=COLOR_TEXT_MAIN, borderwidth=0)
        style.map("Sec.TButton", background=[("active", "#D1D5DB")])

    def init_vars(self, tipo):
        saved = self.last_config.get(tipo, {}) if self.last_config else {}
        defaults = ('N', 180, 200000.0, 500000.0, 10000.0) if tipo == '2011' else ('N', 106, 80000.0, 110000.0, 10000.0)
        return {
            'plano': tk.StringVar(value=saved.get('plano', defaults[0])),
            'prazo': tk.IntVar(value=saved.get('prazo', defaults[1])),
            'credito_ini': tk.DoubleVar(value=saved.get('credito_ini', defaults[2])),
            'credito_fim': tk.DoubleVar(value=saved.get('credito_fim', defaults[3])),
            'passo': tk.DoubleVar(value=saved.get('passo', defaults[4])),
            'novo_arquivo': tk.BooleanVar(value=saved.get('novo_arquivo', False))
        }

    def init_vars_especial(self):
        saved = self.last_config.get('esp', {}) if self.last_config else {}
        return {
            'id_tabela': tk.StringVar(value=saved.get('id_tabela', "custom01")), 
            'nome_real': tk.StringVar(value=saved.get('nome_real', "Minha Tabela")), 
            'plano_tipo': tk.StringVar(value=saved.get('plano_tipo', "N")), 
            'adm': tk.DoubleVar(value=saved.get('adm', 25.0)),
            'seguro': tk.DoubleVar(value=saved.get('seguro', 0.059)),
            'prazo': tk.IntVar(value=saved.get('prazo', 180)),
            'credito_ini': tk.DoubleVar(value=saved.get('credito_ini', 200000.0)),
            'credito_fim': tk.DoubleVar(value=saved.get('credito_fim', 500000.0)),
            'passo': tk.DoubleVar(value=saved.get('passo', 10000.0)),
            'novo_arquivo': tk.BooleanVar(value=saved.get('novo_arquivo', False))
        }

    # --- Helpers UI ---
    def add_linha_compacta(self, parent, label_text, variable, row, col, tipo="texto", width=10):
        cell = ttk.Frame(parent, style="Main.TFrame")
        cell.grid(row=row, column=col, padx=5, pady=3, sticky='ew')
        ttk.Label(cell, text=label_text).pack(anchor='w')
        row_cont = ttk.Frame(cell, style="Main.TFrame")
        row_cont.pack(fill='x')
        if tipo == "moeda": ttk.Label(row_cont, text="R$", style="Sub.TLabel").pack(side='left', padx=(0,2))
        entry = ttk.Entry(row_cont, textvariable=variable, width=width)
        entry.pack(side='left', fill='x', expand=True)
        sufixo = " %" if tipo == "porcentagem" else ("m" if tipo == "numero" and "Prazo" in label_text else "")
        if sufixo: ttk.Label(row_cont, text=sufixo, style="Sub.TLabel").pack(side='left')

    # --- Setup das Abas Originais (Mantido) ---
    def setup_tab_padrao(self, parent, key, radio_labels, radio_values):
        content = ttk.Frame(parent, style="Main.TFrame", padding=10)
        content.pack(fill='both', expand=True)
        lf_plano = ttk.LabelFrame(content, text="PLANO", style="Card.TLabelframe", padding=5)
        lf_plano.pack(fill='x', pady=(0, 10))
        for text, val in zip(radio_labels, radio_values):
            ttk.Radiobutton(lf_plano, text=text, variable=self.vars[key]['plano'], value=val).pack(side='left', padx=10)
        lf_val = ttk.LabelFrame(content, text="VALORES", style="Card.TLabelframe", padding=8)
        lf_val.pack(fill='x', pady=(0, 10))
        self.add_linha_compacta(lf_val, "Prazo", self.vars[key]['prazo'], 0, 0, "numero")
        self.add_linha_compacta(lf_val, "Passo", self.vars[key]['passo'], 0, 1, "moeda")
        self.add_linha_compacta(lf_val, "Crédito Inicial", self.vars[key]['credito_ini'], 1, 0, "moeda")
        self.add_linha_compacta(lf_val, "Crédito Final", self.vars[key]['credito_fim'], 1, 1, "moeda")
        lf_val.columnconfigure(0, weight=1); lf_val.columnconfigure(1, weight=1)
        ttk.Checkbutton(content, text="Criar NOVO arquivo", variable=self.vars[key]['novo_arquivo']).pack(anchor='w')
        ttk.Button(content, text="GERAR TABELA", style="Action.TButton", command=lambda: self.gerar_padrao(key)).pack(fill='x', pady=10, ipady=5)

    def setup_tab_especial(self):
        content = ttk.Frame(self.tab_especial, style="Main.TFrame", padding=10)
        content.pack(fill='both', expand=True)
        key = 'esp'
        lf_id = ttk.LabelFrame(content, text="IDENTIFICAÇÃO", style="Card.TLabelframe", padding=5)
        lf_id.pack(fill='x', pady=(0, 8))
        self.add_linha_compacta(lf_id, "ID (sem espaços)", self.vars[key]['id_tabela'], 0, 0, "texto")
        self.add_linha_compacta(lf_id, "Nome da Tabela", self.vars[key]['nome_real'], 0, 1, "texto")
        lf_id.columnconfigure(0, weight=1); lf_id.columnconfigure(1, weight=2)
        mid_frame = ttk.Frame(content, style="Main.TFrame")
        mid_frame.pack(fill='x', pady=(0, 8))
        lf_plano = ttk.LabelFrame(mid_frame, text="PLANO", style="Card.TLabelframe", padding=5)
        lf_plano.pack(side='left', fill='both', expand=True, padx=(0, 5))
        for i, (t, v) in enumerate([("N (100%)", "N"), ("L (75%)", "L"), ("SL (50%)", "SL")]):
            ttk.Radiobutton(lf_plano, text=t, variable=self.vars[key]['plano_tipo'], value=v).pack(anchor='w')
        lf_taxas = ttk.LabelFrame(mid_frame, text="TAXAS", style="Card.TLabelframe", padding=5)
        lf_taxas.pack(side='right', fill='both', expand=True)
        self.add_linha_compacta(lf_taxas, "Adm", self.vars[key]['adm'], 0, 0, "porcentagem", width=6)
        self.add_linha_compacta(lf_taxas, "Seguro", self.vars[key]['seguro'], 1, 0, "porcentagem", width=6)
        lf_range = ttk.LabelFrame(content, text="VALORES", style="Card.TLabelframe", padding=5)
        lf_range.pack(fill='x', pady=(0, 8))
        self.add_linha_compacta(lf_range, "Prazo", self.vars[key]['prazo'], 0, 0, "numero")
        self.add_linha_compacta(lf_range, "Passo", self.vars[key]['passo'], 0, 1, "moeda")
        self.add_linha_compacta(lf_range, "Início", self.vars[key]['credito_ini'], 1, 0, "moeda")
        self.add_linha_compacta(lf_range, "Fim", self.vars[key]['credito_fim'], 1, 1, "moeda")
        lf_range.columnconfigure(0, weight=1); lf_range.columnconfigure(1, weight=1)
        bottom_frame = ttk.Frame(content, style="Main.TFrame")
        bottom_frame.pack(fill='x', pady=5)
        ttk.Checkbutton(bottom_frame, text="Novo arquivo", variable=self.vars[key]['novo_arquivo']).pack(side='left')
        ttk.Button(content, text="GERAR ESPECIAL", style="Action.TButton", command=self.gerar_especial).pack(fill='x', ipady=5)

    # --- NOVA ABA: PDF ---
    def setup_tab_pdf(self):
        content = ttk.Frame(self.tab_pdf, style="Main.TFrame", padding=15)
        content.pack(fill='both', expand=True)

        # Seleção de Arquivo
        lf_sel = ttk.LabelFrame(content, text="SELEÇÃO DE ARQUIVO", style="Card.TLabelframe", padding=10)
        lf_sel.pack(fill='x', pady=(0, 10))

        row_file = ttk.Frame(lf_sel, style="Main.TFrame")
        row_file.pack(fill='x')
        
        # Botão Escolher
        ttk.Button(row_file, text="📁 Selecionar PDF...", style="Sec.TButton", command=self.selecionar_pdf).pack(side='left', padx=(0, 10))
        # Label com o caminho
        lbl_path = ttk.Label(row_file, textvariable=self.vars['pdf']['path'], foreground=COLOR_TEXT_SUB, width=40)
        lbl_path.pack(side='left', fill='x', expand=True)

        # Botão Processar
        ttk.Button(content, text="⚙️ PROCESSAR E SALVAR DADOS", style="Action.TButton", command=self.executar_processamento_pdf).pack(fill='x', pady=10, ipady=6)

        # Área de Log (Terminal Visual)
        lf_log = ttk.LabelFrame(content, text="LOG DE PROCESSAMENTO", style="Card.TLabelframe", padding=5)
        lf_log.pack(fill='both', expand=True)
        
        self.txt_log = scrolledtext.ScrolledText(lf_log, height=10, font=("Consolas", 8), state='disabled', bg="#F3F4F6", relief="flat")
        self.txt_log.pack(fill='both', expand=True)

    def log_pdf(self, message):
        """Escreve no terminal visual da aba PDF"""
        self.txt_log.config(state='normal')
        self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state='disabled')
        self.root.update_idletasks() # Força atualização da tela

    def selecionar_pdf(self):
        path = filedialog.askopenfilename(title="Selecione o PDF da Assembleia", filetypes=[("Arquivos PDF", "*.pdf")])
        if path:
            self.vars['pdf']['path'].set(path)
            self.txt_log.config(state='normal')
            self.txt_log.delete(1.0, tk.END) # Limpa log anterior
            self.txt_log.config(state='disabled')
            self.log_pdf(f"Arquivo selecionado: {os.path.basename(path)}")
            self.log_pdf("Pronto para processar.")

    def executar_processamento_pdf(self):
        pdf_path = self.vars['pdf']['path'].get()
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showwarning("Atenção", "Selecione um arquivo PDF válido primeiro.")
            return

        # Executar em Thread para não travar a UI durante leitura do PDF
        self.btn_bloqueio = True # (Implementar bloqueio de botões seria ideal, mas simplificaremos)
        threading.Thread(target=self._thread_pdf, args=(pdf_path,)).start()

    def _thread_pdf(self, pdf_path):
        self.log_pdf("-" * 40)
        self.log_pdf("INICIANDO EXTRAÇÃO...")
        
        # 1. Extração
        dados = extrair_dados_pdf(pdf_path, callback_log=self.log_pdf)
        
        if not dados:
            self.log_pdf("❌ Nenhum dado válido encontrado ou erro na leitura.")
            return

        self.log_pdf(f"✅ Extração concluída. {len(dados)} grupos identificados.")
        self.log_pdf("💾 Salvando em 'estatisticas_grupos.json'...")

        # 2. Salvamento (Merge)
        try:
            novos, atualizados = atualizar_estatisticas_json(dados)
            self.log_pdf("-" * 40)
            self.log_pdf(f"RESULTADO FINAL:")
            self.log_pdf(f"➕ Grupos Novos: {novos}")
            self.log_pdf(f"🔄 Grupos Atualizados: {atualizados}")
            self.log_pdf(f"📁 Arquivo salvo com sucesso: {ESTATISTICAS_FILE}")
            messagebox.showinfo("Concluído", f"Processamento finalizado!\nNovos: {novos}\nAtualizados: {atualizados}")
        except Exception as e:
            self.log_pdf(f"❌ Erro ao salvar JSON: {str(e)}")


    # --- MÉTODOS ORIGINAIS (MANTIDOS) ---
    def salvar_estado_atual(self):
        dados = {k: {sk: sv.get() for sk, sv in v.items()} for k, v in self.vars.items() if k != 'pdf'}
        salvar_config(dados)
    
    def get_caminho_salvamento(self, novo_arquivo):
        if novo_arquivo: return filedialog.asksaveasfilename(title="Salvar Novo", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="tabelas.json")
        return filedialog.askopenfilename(title="Abrir JSON", filetypes=[("JSON", "*.json")]) or None

    def gerar_padrao(self, grupo):
        self.salvar_estado_atual() 
        d = self.vars[grupo]
        pl = d['plano'].get()
        chave = f"t_{('imovel' if grupo=='2011' else 'auto')}{grupo}_{('normal' if pl=='N' else pl)}"
        try:
            res = calcular_simulacao(grupo, pl, d['prazo'].get(), d['credito_ini'].get(), d['credito_fim'].get(), d['passo'].get())
            path = self.get_caminho_salvamento(d['novo_arquivo'].get())
            if path: salvar_json(path, chave, res, substituir=d['novo_arquivo'].get()); messagebox.showinfo("OK", "Gerado!")
        except Exception as e: messagebox.showerror("Erro", str(e))

    def gerar_especial(self):
        self.salvar_estado_atual()
        d = self.vars['esp']
        pl = d['plano_tipo'].get()
        map_s = {"N": "_normal", "L": "_L", "SL": "_SL"}
        chave = f"t_{d['id_tabela'].get().strip()}{map_s.get(pl, '')}"
        seg = d['seguro'].get()
        cat = "IMOVEL" if abs(seg - 0.059) < 0.001 else ("AUTO" if abs(seg - 0.084) < 0.001 else "OUTROS")
        meta = {"id": chave, "name": d['nome_real'].get(), "category": cat, "plan": pl, "taxaAdmin": d['adm'].get()/100, "fundoReserva": 0.03, "seguroPct": round(seg/100, 5), "maxLanceEmbutido": 0.25}
        try:
            res = calcular_simulacao("ESPECIAL", "CUSTOM", d['prazo'].get(), d['credito_ini'].get(), d['credito_fim'].get(), d['passo'].get(), custom_data={'fator': {"N":1.0,"L":0.75,"SL":0.5}[pl], 'adm': d['adm'].get()/100, 'fundo': 0.03, 'seguro': seg/100})
            path = self.get_caminho_salvamento(d['novo_arquivo'].get())
            if path: salvar_json(path, chave, res, substituir=d['novo_arquivo'].get(), metadata_item=meta); messagebox.showinfo("OK", "Gerado!")
        except Exception as e: messagebox.showerror("Erro", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = ConsorcioApp(root)
    root.mainloop()
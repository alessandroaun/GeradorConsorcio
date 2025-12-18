import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import threading
import os
import json
import copy

from gerador import calcular_simulacao
from json_utils import salvar_json, salvar_config, carregar_config, atualizar_estatisticas_json, ESTATISTICAS_FILE
from pdf_processor import extrair_dados_pdf

# --- DESIGN SYSTEM ---
COLOR_BG = "#F9FAFB"
COLOR_CARD = "#FFFFFF"
COLOR_PRIMARY = "#2563EB"     # Azul Royal
COLOR_DANGER = "#DC2626"      # Vermelho
COLOR_WARNING = "#F59E0B"     # Amarelo/Laranja
COLOR_SUCCESS = "#059669"     # Verde
COLOR_TEXT_MAIN = "#111827"
COLOR_TEXT_SUB = "#6B7280"
COLOR_BORDER = "#E5E7EB"

class ConsorcioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gerenciador de Banco de Dados - Simulador Recon   -->   Desenvolvido por Alessandro Uchoa  v1.0")
        self.root.geometry("690x670") # Largura ajustada
        self.root.configure(bg=COLOR_BG)
        
        self.setup_styles()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)

        self.tab_2011 = ttk.Frame(self.notebook, style="Main.TFrame")
        self.tab_5121 = ttk.Frame(self.notebook, style="Main.TFrame")
        self.tab_especial = ttk.Frame(self.notebook, style="Main.TFrame")
        self.tab_editor = ttk.Frame(self.notebook, style="Main.TFrame")
        self.tab_pdf = ttk.Frame(self.notebook, style="Main.TFrame")
        self.tab_relacao = ttk.Frame(self.notebook, style="Main.TFrame") 

        self.notebook.add(self.tab_2011, text=' Editar 2011 ')
        self.notebook.add(self.tab_5121, text=' Editar 5121 ')
        self.notebook.add(self.tab_especial, text=' Criar Tabela ')
        self.notebook.add(self.tab_editor, text=' Editar Tabelas ')
        self.notebook.add(self.tab_pdf, text=' Leitor PDF das Assembleias ')
        self.notebook.add(self.tab_relacao, text=' Relação de Grupos ') 

        self.last_config = carregar_config()

        # Variáveis de Estado do Editor de Tabelas
        self.editor_filepath = None
        self.editor_data = {"metadata": [], "data": {}} 
        self.editor_backup = {"metadata": [], "data": {}}
        self.selected_table_id = None 

        # Variáveis de Estado da Aba Relação Grupos
        self.relacao_filepath = None
        self.relacao_data = {} 
        self.relacao_backup = {} # Backup para desfazer
        self.relacao_vars_cache = {} 
        self.relacao_selected_grupo = None

        self.vars = {
            '2011': self.init_vars('2011'),
            '5121': self.init_vars('5121'),
            'esp': self.init_vars_especial(),
            'pdf': {'path': tk.StringVar()},
            'editor': {
                'id': tk.StringVar(),
                'name': tk.StringVar(),
                'category': tk.StringVar(),
                'plan': tk.StringVar(),
                'adm': tk.DoubleVar(),
                'fundo': tk.DoubleVar(),
                'seguro': tk.DoubleVar()
            }
        }

        self.setup_tab_padrao(self.tab_2011, "2011", ["Normal", "Light", "SuperLight"], ["N", "L", "SL"])
        self.setup_tab_padrao(self.tab_5121, "5121", ["Normal", "Light"], ["N", "L"])
        self.setup_tab_especial()
        self.setup_tab_editor()
        self.setup_tab_pdf()
        self.setup_tab_relacao() 

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

        style.configure("Danger.TButton", font=("Segoe UI", 9, "bold"), background=COLOR_DANGER, foreground="white")
        style.map("Danger.TButton", background=[("active", "#991B1B")])

        style.configure("Warning.TButton", font=("Segoe UI", 9, "bold"), background=COLOR_WARNING, foreground="white")
        style.map("Warning.TButton", background=[("active", "#D97706")])

        style.configure("Sec.TButton", font=("Segoe UI", 8), background="#E5E7EB", foreground=COLOR_TEXT_MAIN, borderwidth=0)
        style.map("Sec.TButton", background=[("active", "#D1D5DB")])

        style.configure("Treeview", background="white", fieldbackground="white", font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

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
            'novo_arquivo': tk.BooleanVar(value=saved.get('novo_arquivo', False)),
            'apenas_csv': tk.BooleanVar(value=saved.get('apenas_csv', False)) # NOVA VARIAVEL
        }

    # --- UI Helpers ---
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

    # --- ABAS ORIGINAIS ---
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
        
        # Correção visual e funcional
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
        for i, (t, v) in enumerate([("NORMAL (100%)", "NORMAL"), ("LIGHT (75%)", "LIGHT"), ("SUPERLIGHT (50%)", "SUPERLIGHT")]):
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
        
        # Área Inferior com a Nova Checkbox
        bottom_frame = ttk.Frame(content, style="Main.TFrame")
        bottom_frame.pack(fill='x', pady=5)
        
        ttk.Checkbutton(bottom_frame, text="Novo arquivo", variable=self.vars[key]['novo_arquivo']).pack(side='left', padx=(0, 10))
        # NOVA CAIXA DE SELEÇÃO
        ttk.Checkbutton(bottom_frame, text="Tabela Apenas C/SV", variable=self.vars[key]['apenas_csv']).pack(side='left')
        
        ttk.Button(content, text="GERAR ESPECIAL", style="Action.TButton", command=self.gerar_especial).pack(fill='x', ipady=5)

    # --- ABA EDITOR JSON ---
    def setup_tab_editor(self):
        content = ttk.Frame(self.tab_editor, style="Main.TFrame", padding=10)
        content.pack(fill='both', expand=True)
        top_bar = ttk.Frame(content, style="Main.TFrame")
        top_bar.pack(fill='x', pady=(0, 10))
        ttk.Button(top_bar, text="📂 Abrir JSON", style="Sec.TButton", command=self.editor_carregar_arquivo).pack(side='left', padx=(0, 5))
        self.lbl_editor_status = ttk.Label(top_bar, text="...", foreground=COLOR_TEXT_SUB)
        self.lbl_editor_status.pack(side='left', padx=5)
        ttk.Button(top_bar, text="💾 Salvar Disco", style="Action.TButton", command=self.editor_salvar_disco).pack(side='right', padx=(5, 0))
        ttk.Button(top_bar, text="↩ Desfazer", style="Warning.TButton", command=self.editor_reverter).pack(side='right')
        paned = tk.PanedWindow(content, orient=tk.HORIZONTAL, bg=COLOR_BG, sashwidth=4, showhandle=True)
        paned.pack(fill='both', expand=True)
        frame_list = ttk.Frame(paned, style="Main.TFrame")
        paned.add(frame_list, width=200)
        ttk.Label(frame_list, text="TABELAS", font=("Segoe UI", 8, "bold"), foreground=COLOR_TEXT_SUB).pack(anchor='w', pady=(0, 5))
        scroll_lst = ttk.Scrollbar(frame_list)
        scroll_lst.pack(side='right', fill='y')
        self.lst_tabelas = tk.Listbox(frame_list, font=("Segoe UI", 9), borderwidth=1, relief="solid", yscrollcommand=scroll_lst.set)
        self.lst_tabelas.pack(side='left', fill='both', expand=True)
        scroll_lst.config(command=self.lst_tabelas.yview)
        self.lst_tabelas.bind('<<ListboxSelect>>', self.editor_selecionar_tabela)
        self.frame_edit = ttk.Frame(paned, style="Main.TFrame", padding=(10, 0, 0, 0))
        paned.add(self.frame_edit)
        lf_meta = ttk.LabelFrame(self.frame_edit, text="METADADOS", style="Card.TLabelframe", padding=10)
        lf_meta.pack(fill='x', pady=(0, 10))
        self.add_linha_compacta(lf_meta, "ID (Chave)", self.vars['editor']['id'], 0, 0, "texto", width=20)
        self.add_linha_compacta(lf_meta, "Nome Exib.", self.vars['editor']['name'], 0, 1, "texto", width=20)
        self.add_linha_compacta(lf_meta, "Categoria", self.vars['editor']['category'], 1, 0, "texto")
        self.add_linha_compacta(lf_meta, "Plano", self.vars['editor']['plan'], 1, 1, "texto")
        self.add_linha_compacta(lf_meta, "Tx. Adm", self.vars['editor']['adm'], 2, 0, "texto")
        self.add_linha_compacta(lf_meta, "Seguro", self.vars['editor']['seguro'], 2, 1, "texto")
        lf_meta.columnconfigure(0, weight=1); lf_meta.columnconfigure(1, weight=1)
        btn_meta = ttk.Frame(lf_meta, style="Main.TFrame")
        btn_meta.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky='ew')
        ttk.Button(btn_meta, text="Atualizar Meta", style="Sec.TButton", command=self.editor_atualizar_metadados).pack(side='left', fill='x', expand=True, padx=(0, 5))
        ttk.Button(btn_meta, text="Converter p/ Seguro Obrigatório", style="Warning.TButton", command=self.editor_converter_seguro).pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(btn_meta, text="Excluir Tabela", style="Danger.TButton", command=self.editor_excluir_tabela).pack(side='right', fill='x', expand=True, padx=(5, 0))
        lf_data = ttk.LabelFrame(self.frame_edit, text="DADOS (Expanda para ver prazos)", style="Card.TLabelframe", padding=10)
        lf_data.pack(fill='both', expand=True)
        self.tree_data = ttk.Treeview(lf_data, columns=("detalhes"), show='tree headings', height=8)
        self.tree_data.heading("#0", text="Crédito / Prazo")
        self.tree_data.heading("detalhes", text="Valores das Parcelas")
        self.tree_data.column("#0", width=100); self.tree_data.column("detalhes", width=200)
        scroll_tree = ttk.Scrollbar(lf_data, orient="vertical", command=self.tree_data.yview)
        self.tree_data.configure(yscrollcommand=scroll_tree.set)
        self.tree_data.pack(side='left', fill='both', expand=True)
        scroll_tree.pack(side='right', fill='y')
        ttk.Button(lf_data, text="Excluir Item\nSelecionado", style="Danger.TButton", command=self.editor_excluir_item).pack(side='top', fill='x', pady=(5, 0))

    # --- Lógica Editor ---
    def editor_carregar_arquivo(self):
        path = filedialog.askopenfilename(title="Abrir JSON", filetypes=[("JSON", "*.json")])
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
            if "metadata" not in data or "data" not in data: messagebox.showerror("Erro", "JSON inválido."); return
            self.editor_filepath = path; self.editor_data = data; self.editor_backup = copy.deepcopy(data)
            self.lbl_editor_status.config(text=os.path.basename(path), foreground=COLOR_SUCCESS)
            self.editor_refresh_lista(); self.tree_data.delete(*self.tree_data.get_children()); self.selected_table_id = None
        except Exception as e: messagebox.showerror("Erro", f"{e}")

    def editor_refresh_lista(self):
        self.lst_tabelas.delete(0, tk.END)
        if not self.editor_data: return
        for item in self.editor_data["metadata"]: self.lst_tabelas.insert(tk.END, item.get("id", "?"))

    def editor_selecionar_tabela(self, event):
        sel = self.lst_tabelas.curselection()
        if not sel: return
        t_id = self.lst_tabelas.get(sel[0])
        self.selected_table_id = t_id
        meta = next((m for m in self.editor_data["metadata"] if m["id"] == t_id), None)
        if meta:
            self.vars['editor']['id'].set(meta.get('id', ''))
            self.vars['editor']['name'].set(meta.get('name', ''))
            self.vars['editor']['category'].set(meta.get('category', ''))
            self.vars['editor']['plan'].set(meta.get('plan', ''))
            self.vars['editor']['adm'].set(meta.get('taxaAdmin', 0.0))
            self.vars['editor']['fundo'].set(meta.get('fundoReserva', 0.0))
            self.vars['editor']['seguro'].set(meta.get('seguroPct', 0.0))
        self.tree_data.delete(*self.tree_data.get_children())
        rows = self.editor_data["data"].get(t_id, [])
        rows.sort(key=lambda x: x.get('credito', 0))
        for i, r in enumerate(rows):
            credito = r.get('credito', 0)
            cred_fmt = f"R$ {credito:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            parent_id = self.tree_data.insert("", "end", iid=f"c_{i}", text=cred_fmt, values=("Expandir para ver prazos",), open=False)
            prazos = r.get('prazos', [])
            prazos.sort(key=lambda x: x.get('prazo', 0))
            for j, p in enumerate(prazos):
                prazo_meses = p.get('prazo', 0)
                val_unico = p.get('parcela', None)
                val_csv = p.get('parcela_CSV', 0)
                val_ssv = p.get('parcela_SSV', None)
                if val_unico is not None: detalhe = f"Parcela: R$ {val_unico:.2f} (Sem Seguro)"
                else:
                    detalhe = f"CSV: R$ {val_csv:.2f}"
                    if val_ssv is not None: detalhe += f" | SSV: R$ {val_ssv:.2f}"
                    else: detalhe += " | SSV: (Obrigatório)"
                self.tree_data.insert(parent_id, "end", iid=f"p_{i}_{j}", text=f"{prazo_meses} meses", values=(detalhe,))

    def editor_atualizar_metadados(self):
        if not self.selected_table_id: return
        meta_list = self.editor_data["metadata"]
        for m in meta_list:
            if m["id"] == self.selected_table_id:
                m["name"] = self.vars['editor']['name'].get()
                m["category"] = self.vars['editor']['category'].get()
                m["plan"] = self.vars['editor']['plan'].get()
                m["taxaAdmin"] = self.vars['editor']['adm'].get()
                m["seguroPct"] = self.vars['editor']['seguro'].get()
                messagebox.showinfo("OK", "Metadados atualizados em memória.")
                return

    def editor_converter_seguro(self):
        t_id = self.selected_table_id
        if not t_id: return
        rows = self.editor_data["data"].get(t_id, [])
        if not rows: return
        alteracoes = 0
        for r in rows:
            for p in r.get('prazos', []):
                if 'parcela_SSV' in p or ('parcela_CSV' in p and 'parcela' not in p):
                    if 'parcela_SSV' in p: del p['parcela_SSV']
                    if 'parcela_CSV' in p: val = p.pop('parcela_CSV'); p['parcela'] = val
                    alteracoes += 1
        if alteracoes == 0: messagebox.showinfo("Aviso", "Sem dados para alterar.")
        else:
            self.editor_selecionar_tabela(None)
            msg = (f"Sucesso! {alteracoes} prazos convertidos.\nSUGESTÃO: Se virou Light/SL, ajuste o ID nos Metadados.")
            messagebox.showinfo("Conversão Concluída", msg)

    def editor_excluir_tabela(self):
        t_id = self.selected_table_id
        if not t_id: return
        if not messagebox.askyesno("Confirmar", f"Excluir tabela '{t_id}'?"): return
        self.editor_data["metadata"] = [m for m in self.editor_data["metadata"] if m["id"] != t_id]
        if t_id in self.editor_data["data"]: del self.editor_data["data"][t_id]
        self.editor_refresh_lista(); self.tree_data.delete(*self.tree_data.get_children()); self.selected_table_id = None

    def editor_excluir_item(self):
        sel = self.tree_data.selection()
        if not sel: return
        item_id = sel[0]
        t_id = self.selected_table_id
        rows = self.editor_data["data"].get(t_id, [])
        if item_id.startswith("c_"):
            idx_cred = int(item_id.split("_")[1])
            if not messagebox.askyesno("Excluir Crédito", "Deseja excluir TODO o crédito?"): return
            del rows[idx_cred]; self.editor_data["data"][t_id] = rows; self.editor_selecionar_tabela(None)
        elif item_id.startswith("p_"):
            parts = item_id.split("_")
            idx_cred = int(parts[1])
            idx_prazo = int(parts[2])
            cred_row = rows[idx_cred]
            prazos = cred_row.get('prazos', [])
            if len(prazos) <= 1:
                if messagebox.askyesno("Aviso", "Único prazo. Excluir crédito inteiro?"): del rows[idx_cred]; self.editor_data["data"][t_id] = rows; self.editor_selecionar_tabela(None)
                return
            if not messagebox.askyesno("Excluir Prazo", "Excluir apenas esta opção?"): return
            rows.sort(key=lambda x: x.get('credito', 0))
            rows[idx_cred]['prazos'].sort(key=lambda x: x.get('prazo', 0))
            del rows[idx_cred]['prazos'][idx_prazo]; self.editor_data["data"][t_id] = rows; self.editor_selecionar_tabela(None)

    def editor_reverter(self):
        if not self.editor_backup: return
        if messagebox.askyesno("Reverter", "Desfazer alterações?"): self.editor_data = copy.deepcopy(self.editor_backup); self.editor_refresh_lista(); self.tree_data.delete(*self.tree_data.get_children()); self.selected_table_id = None

    def editor_salvar_disco(self):
        if not self.editor_filepath: return
        try:
            with open(self.editor_filepath, 'w', encoding='utf-8') as f: json.dump(self.editor_data, f, indent=4, ensure_ascii=False)
            self.editor_backup = copy.deepcopy(self.editor_data); messagebox.showinfo("Sucesso", "Salvo!")
        except Exception as e: messagebox.showerror("Erro", f"{e}")

    # --- ABA PDF ---
    def setup_tab_pdf(self):
        content = ttk.Frame(self.tab_pdf, style="Main.TFrame", padding=15)
        content.pack(fill='both', expand=True)
        lf_sel = ttk.LabelFrame(content, text="SELEÇÃO DE ARQUIVO", style="Card.TLabelframe", padding=10)
        lf_sel.pack(fill='x', pady=(0, 10))
        row_file = ttk.Frame(lf_sel, style="Main.TFrame")
        row_file.pack(fill='x')
        ttk.Button(row_file, text="📁 Selecionar PDF...", style="Sec.TButton", command=self.selecionar_pdf).pack(side='left', padx=(0, 10))
        lbl_path = ttk.Label(row_file, textvariable=self.vars['pdf']['path'], foreground=COLOR_TEXT_SUB, width=40)
        lbl_path.pack(side='left', fill='x', expand=True)
        ttk.Button(content, text="⚙️ PROCESSAR E SALVAR DADOS", style="Action.TButton", command=self.executar_processamento_pdf).pack(fill='x', pady=10, ipady=6)
        lf_log = ttk.LabelFrame(content, text="LOG DE PROCESSAMENTO", style="Card.TLabelframe", padding=5)
        lf_log.pack(fill='both', expand=True)
        self.txt_log = scrolledtext.ScrolledText(lf_log, height=10, font=("Consolas", 8), state='disabled', bg="#F3F4F6", relief="flat")
        self.txt_log.pack(fill='both', expand=True)

    def log_pdf(self, message):
        self.txt_log.config(state='normal'); self.txt_log.insert(tk.END, message + "\n"); self.txt_log.see(tk.END); self.txt_log.config(state='disabled'); self.root.update_idletasks() 

    def selecionar_pdf(self):
        path = filedialog.askopenfilename(title="Selecione o PDF da Assembleia", filetypes=[("Arquivos PDF", "*.pdf")])
        if path: self.vars['pdf']['path'].set(path); self.txt_log.config(state='normal'); self.txt_log.delete(1.0, tk.END); self.txt_log.config(state='disabled'); self.log_pdf(f"Arquivo selecionado: {os.path.basename(path)}"); self.log_pdf("Pronto para processar.")

    def executar_processamento_pdf(self):
        pdf_path = self.vars['pdf']['path'].get()
        if not pdf_path or not os.path.exists(pdf_path): messagebox.showwarning("Atenção", "Selecione um PDF válido."); return
        threading.Thread(target=self._thread_pdf, args=(pdf_path,)).start()

    def _thread_pdf(self, pdf_path):
        self.log_pdf("-" * 40); self.log_pdf("INICIANDO EXTRAÇÃO...")
        dados = extrair_dados_pdf(pdf_path, callback_log=self.log_pdf)
        if not dados: self.log_pdf("❌ Nenhum dado válido encontrado."); return
        self.log_pdf(f"✅ Extração concluída. {len(dados)} grupos identificados."); self.log_pdf("💾 Salvando...")
        try:
            novos, atualizados = atualizar_estatisticas_json(dados)
            self.log_pdf("-" * 40); self.log_pdf(f"RESULTADO FINAL:"); self.log_pdf(f"➕ Novos: {novos}"); self.log_pdf(f"🔄 Atualizados: {atualizados}")
            self.log_pdf(f"📁 Salvo em: {ESTATISTICAS_FILE}")
            messagebox.showinfo("Concluído", f"Processamento finalizado!\nNovos: {novos}\nAtualizados: {atualizados}")
        except Exception as e: self.log_pdf(f"❌ Erro ao salvar JSON: {str(e)}")

    # =========================================================================
    # NOVA ABA: RELAÇÃO DE GRUPOS
    # =========================================================================
    def setup_tab_relacao(self):
        content = ttk.Frame(self.tab_relacao, style="Main.TFrame", padding=10)
        content.pack(fill='both', expand=True)

        # 1. Top Bar
        top_bar = ttk.Frame(content, style="Main.TFrame")
        top_bar.pack(fill='x', pady=(0, 10))
        ttk.Button(top_bar, text="📁 Abrir relacao_grupos.json", style="Sec.TButton", command=self.relacao_carregar).pack(side='left', padx=(0, 5))
        self.lbl_relacao_status = ttk.Label(top_bar, text="...", foreground=COLOR_TEXT_SUB)
        self.lbl_relacao_status.pack(side='left', padx=5)
        
        # Botões de Ação Topo
        ttk.Button(top_bar, text="💾 Salvar (Validação)", style="Action.TButton", command=self.relacao_salvar).pack(side='right', padx=(5, 0))
        ttk.Button(top_bar, text="↩ Desfazer", style="Warning.TButton", command=self.relacao_reverter).pack(side='right')

        # 2. Painel Dividido
        paned = tk.PanedWindow(content, orient=tk.HORIZONTAL, bg=COLOR_BG, sashwidth=4, showhandle=True)
        paned.pack(fill='both', expand=True)

        # Esquerda: Lista de Grupos
        frame_list = ttk.Frame(paned, style="Main.TFrame")
        paned.add(frame_list, width=220)

        # Botões Grupos
        btn_grp_frame = ttk.Frame(frame_list, style="Main.TFrame")
        btn_grp_frame.pack(fill='x', pady=(0, 5))
        ttk.Button(btn_grp_frame, text="➕ Novo Grupo", style="Sec.TButton", command=self.relacao_novo_grupo).pack(side='left', fill='x', expand=True, padx=(0,2))
        ttk.Button(btn_grp_frame, text="🗑️ Excluir Grupo", style="Danger.TButton", command=self.relacao_excluir_grupo).pack(side='right', fill='x', expand=True, padx=(2,0))
        
        scroll_lst = ttk.Scrollbar(frame_list)
        scroll_lst.pack(side='right', fill='y')
        self.lst_grupos = tk.Listbox(frame_list, font=("Segoe UI", 9), borderwidth=1, relief="solid", yscrollcommand=scroll_lst.set)
        self.lst_grupos.pack(side='left', fill='both', expand=True)
        scroll_lst.config(command=self.lst_grupos.yview)
        self.lst_grupos.bind('<<ListboxSelect>>', self.relacao_selecionar_grupo)

        # Direita: Edição de Campos Dinâmicos (Scrollable)
        right_panel = ttk.Frame(paned, style="Main.TFrame", padding=(10, 0, 0, 0))
        paned.add(right_panel)

        # Barra de Ferramentas de Campos
        toolbar_fields = ttk.LabelFrame(right_panel, text="Gerenciar Entradas de Valores (Campos)", style="Card.TLabelframe", padding=5)
        toolbar_fields.pack(fill='x', pady=(0, 5))
        
        ttk.Button(toolbar_fields, text="➕ Adicionar Campo\n          (Global)", style="Sec.TButton", command=self.relacao_add_global_field).pack(side='left', padx=(0, 5))
        ttk.Button(toolbar_fields, text="➖ Excluir Campo\n          (Global)", style="Warning.TButton", command=self.relacao_del_global_field).pack(side='right', padx=(5, 0))
        ttk.Button(toolbar_fields, text="➖ Excluir Campo\n      (Deste Grupo)", style="Sec.TButton", command=self.relacao_del_local_field).pack(side='right')

        # Canvas para scroll dos campos
        self.canvas_relacao = tk.Canvas(right_panel, bg=COLOR_BG, highlightthickness=0)
        scroll_y = ttk.Scrollbar(right_panel, orient="vertical", command=self.canvas_relacao.yview)
        self.frame_dynamic_fields = ttk.Frame(self.canvas_relacao, style="Main.TFrame")

        self.frame_dynamic_fields.bind("<Configure>", lambda e: self.canvas_relacao.configure(scrollregion=self.canvas_relacao.bbox("all")))
        self.canvas_relacao.create_window((0, 0), window=self.frame_dynamic_fields, anchor="nw")
        self.canvas_relacao.configure(yscrollcommand=scroll_y.set)

        self.canvas_relacao.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

    # --- Lógica Aba Relação ---
    def relacao_carregar(self):
        path = filedialog.askopenfilename(title="Abrir relacao_grupos.json", filetypes=[("JSON", "*.json")])
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw_list = json.load(f)
            
            self.relacao_data = {}
            for item in raw_list:
                gid = str(item.get("Grupo", "S/N"))
                self.relacao_data[gid] = item

            # CRIA BACKUP AO CARREGAR
            self.relacao_backup = copy.deepcopy(self.relacao_data)
            
            self.relacao_filepath = path
            self.lbl_relacao_status.config(text=os.path.basename(path), foreground=COLOR_SUCCESS)
            self.relacao_refresh_list()
            self.relacao_limpar_painel()
        except Exception as e: messagebox.showerror("Erro", f"{e}")

    def relacao_refresh_list(self):
        self.lst_grupos.delete(0, tk.END)
        try: sorted_keys = sorted(self.relacao_data.keys(), key=lambda x: int(x))
        except: sorted_keys = sorted(self.relacao_data.keys())
        for k in sorted_keys: self.lst_grupos.insert(tk.END, k)

    def relacao_limpar_painel(self):
        for widget in self.frame_dynamic_fields.winfo_children(): widget.destroy()
        self.relacao_vars_cache = {}
        self.relacao_selected_grupo = None

    def relacao_atualizar_memoria(self):
        if self.relacao_selected_grupo and self.relacao_selected_grupo in self.relacao_data:
            for k, var in self.relacao_vars_cache.items():
                val = var.get()
                # Conversão inteligente
                if k == "Grupo":
                    try: val = int(val)
                    except: pass
                elif k == "Prazo Máximo":
                    try: val = int(val)
                    except: pass
                self.relacao_data[self.relacao_selected_grupo][k] = val
    def _renderizar_campos_grupo(self, grp_id):
        """Método auxiliar para desenhar os campos sem disparar salvamentos automáticos."""
        # Limpa visual
        for widget in self.frame_dynamic_fields.winfo_children(): widget.destroy()
        self.relacao_vars_cache = {}

        dados = self.relacao_data.get(grp_id, {})
        
        ttk.Label(self.frame_dynamic_fields, text=f"Editando Grupo: {grp_id}", font=("Segoe UI", 10, "bold"), foreground=COLOR_PRIMARY).pack(anchor='w', pady=(0, 10))

        # Cria campos
        for key, val in dados.items():
            f = ttk.Frame(self.frame_dynamic_fields, style="Main.TFrame")
            f.pack(fill='x', pady=2)
            
            # Label da chave
            ttk.Label(f, text=key, width=20).pack(side='left')
            
            # Valor
            var = tk.StringVar(value=str(val))
            self.relacao_vars_cache[key] = var
            
            entry = ttk.Entry(f, textvariable=var)
            # Bloqueia edição da chave primária 'Grupo' visualmente
            if key == "Grupo": entry.config(state='readonly') 
            entry.pack(side='left', fill='x', expand=True)
    def relacao_selecionar_grupo(self, event):
        sel = self.lst_grupos.curselection()
        if not sel: return
        
        # 1. Salva o estado do grupo ANTERIOR antes de trocar
        self.relacao_atualizar_memoria() 

        # 2. Define o NOVO grupo
        grp_id = self.lst_grupos.get(sel[0])
        self.relacao_selected_grupo = grp_id
        
        # 3. Renderiza o NOVO grupo
        self._renderizar_campos_grupo(grp_id)

    def relacao_novo_grupo(self):
        if not self.relacao_data: messagebox.showwarning("Aviso", "Carregue um arquivo primeiro."); return
        new_id = simpledialog.askstring("Novo Grupo", "Digite o número do novo Grupo:")
        if not new_id: return
        if new_id in self.relacao_data: messagebox.showerror("Erro", "Grupo já existe."); return

        first_key = list(self.relacao_data.keys())[0]
        template = self.relacao_data[first_key]
        new_obj = {}
        for k in template.keys():
            if k == "Grupo":
                try: new_obj[k] = int(new_id)
                except: new_obj[k] = new_id
            else: new_obj[k] = ""
        
        self.relacao_data[new_id] = new_obj
        self.relacao_refresh_list()
        messagebox.showinfo("Criado", f"Grupo {new_id} criado. Edite agora!")

    def relacao_excluir_grupo(self):
        sel = self.lst_grupos.curselection()
        if not sel: return
        grp_id = self.lst_grupos.get(sel[0])
        
        if messagebox.askyesno("Excluir", f"Tem certeza que deseja apagar o Grupo {grp_id}?"):
            if grp_id == self.relacao_selected_grupo:
                self.relacao_limpar_painel()
            del self.relacao_data[grp_id]
            self.relacao_refresh_list()

    def relacao_add_global_field(self):
        if not self.relacao_data: return
        field_name = simpledialog.askstring("Novo Campo", "Nome da nova chave:")
        if not field_name: return
        for grp in self.relacao_data:
            if field_name not in self.relacao_data[grp]: self.relacao_data[grp][field_name] = ""
        if self.relacao_selected_grupo: self.lst_grupos.event_generate("<<ListboxSelect>>")
        messagebox.showinfo("Sucesso", f"Campo '{field_name}' adicionado a todos.")

    def relacao_del_global_field(self):
        if not self.relacao_data: return
        
        # 1. Salva tudo o que está na tela primeiro para não perder edições pendentes
        self.relacao_atualizar_memoria()

        field_name = simpledialog.askstring("Excluir Campo Global", "Digite o nome Exato da chave para remover de TODOS os grupos:")
        if not field_name: return
        
        # Proteção
        if field_name == "Grupo": messagebox.showerror("Erro", "Não é permitido remover a chave 'Grupo'."); return

        count = 0
        for grp in self.relacao_data:
            if field_name in self.relacao_data[grp]:
                del self.relacao_data[grp][field_name]
                count += 1
        
        if count > 0:
            # 2. Se houver um grupo selecionado na tela, redesenha ele IMEDIATAMENTE puxando da memória atualizada
            if self.relacao_selected_grupo: 
                self._renderizar_campos_grupo(self.relacao_selected_grupo)
            
            messagebox.showinfo("Removido", f"Campo '{field_name}' removido de {count} grupos.")
        else:
            messagebox.showwarning("Aviso", "Campo não encontrado nos grupos.")

    def relacao_del_local_field(self):
        if not self.relacao_selected_grupo: messagebox.showwarning("Aviso", "Selecione um grupo primeiro."); return
        
        # 1. Salva edições pendentes antes de manipular os dados
        self.relacao_atualizar_memoria()

        field_name = simpledialog.askstring("Excluir Campo Local", f"Digite o nome da chave para remover apenas do Grupo {self.relacao_selected_grupo}:")
        if not field_name: return
        
        if field_name == "Grupo": messagebox.showerror("Erro", "Não é permitido remover a chave 'Grupo'."); return

        dados = self.relacao_data[self.relacao_selected_grupo]
        
        if field_name in dados:
            # 2. Remove da memória
            del self.relacao_data[self.relacao_selected_grupo][field_name]
            
            # 3. Redesenha a tela puxando da memória (onde o campo já não existe mais)
            self._renderizar_campos_grupo(self.relacao_selected_grupo)
        else:
            messagebox.showwarning("Aviso", "Campo não encontrado neste grupo.")

    def relacao_reverter(self):
        if not self.relacao_backup: return
        if messagebox.askyesno("Desfazer", "Reverter todas as alterações para o último salvamento/abertura?"):
            self.relacao_data = copy.deepcopy(self.relacao_backup)
            self.relacao_refresh_list()
            self.relacao_limpar_painel()

    def relacao_salvar(self):
        if not self.relacao_filepath: return
        
        self.relacao_atualizar_memoria()

        erros = []
        for grp, dados in self.relacao_data.items():
            for k, v in dados.items():
                if v is None or str(v).strip() == "":
                    erros.append(f"Grupo {grp} -> Campo '{k}' está vazio.")
        
        if erros:
            msg = "Validação Falhou! Valores vazios:\n\n" + "\n".join(erros[:10])
            if len(erros) > 10: msg += "\n... e mais erros."
            messagebox.showerror("Erro", msg)
            return

        final_list = list(self.relacao_data.values())
        try: final_list.sort(key=lambda x: int(x.get("Grupo", 0)))
        except: pass

        try:
            with open(self.relacao_filepath, 'w', encoding='utf-8') as f:
                json.dump(final_list, f, indent=4, ensure_ascii=False)
            
            # ATUALIZA BACKUP APÓS SALVAR
            self.relacao_backup = copy.deepcopy(self.relacao_data)
            messagebox.showinfo("Sucesso", "Arquivo salvo e backup atualizado!")
        except Exception as e:
            messagebox.showerror("Erro ao salvar", f"{e}")

    # --- GERADOR ---
    def salvar_estado_atual(self):
        dados = {k: {sk: sv.get() for sk, sv in v.items()} for k, v in self.vars.items() if k not in ['pdf','editor']}
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
            # CORREÇÃO: Passando o booleano explicitamente
            is_novo = bool(d['novo_arquivo'].get())
            path = self.get_caminho_salvamento(is_novo)
            if path: 
                salvar_json(path, chave, res, substituir=is_novo)
                messagebox.showinfo("OK", "Gerado!")
        except Exception as e: 
            messagebox.showerror("Erro Crítico", f"Falha ao salvar/gerar:\n{str(e)}")

    def gerar_especial(self):
        self.salvar_estado_atual()
        d = self.vars['esp']
        pl = d['plano_tipo'].get()
        map_s = {"NORMAL": "_normal", "LIGHT": "_L", "SUPERLIGHT": "_SL"}
        chave = f"t_{d['id_tabela'].get().strip()}{map_s.get(pl, '')}"
        seg = d['seguro'].get()
        cat = "IMOVEL" if abs(seg - 0.059) < 0.001 else ("AUTO" if abs(seg - 0.084) < 0.001 else "OUTROS")
        meta = {"id": chave, "name": d['nome_real'].get(), "category": cat, "plan": pl, "taxaAdmin": d['adm'].get()/100, "fundoReserva": 0.03, "seguroPct": round(seg/100, 5), "maxLanceEmbutido": 0.25}
        
        try:
            res = calcular_simulacao("ESPECIAL", "CUSTOM", d['prazo'].get(), d['credito_ini'].get(), d['credito_fim'].get(), d['passo'].get(), custom_data={'fator': {"NORMAL":1.0,"LIGHT":0.75,"SUPERLIGHT":0.5}[pl], 'adm': d['adm'].get()/100, 'fundo': 0.03, 'seguro': seg/100})
            
            # LÓGICA DO NOVO CHECKBOX "APENAS CSV"
            if d['apenas_csv'].get():
                for item in res:
                    for p in item['prazos']:
                        # Remove SSV
                        if 'parcela_SSV' in p:
                            del p['parcela_SSV']
                        # Renomeia CSV -> parcela
                        if 'parcela_CSV' in p:
                            p['parcela'] = p.pop('parcela_CSV')

            # CORREÇÃO: Passando o booleano explicitamente
            is_novo = bool(d['novo_arquivo'].get())
            path = self.get_caminho_salvamento(is_novo)
            
            if path: 
                salvar_json(path, chave, res, substituir=is_novo, metadata_item=meta)
                messagebox.showinfo("OK", "Gerado!")
        except Exception as e: 
            messagebox.showerror("Erro Crítico", f"Falha ao salvar/gerar:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConsorcioApp(root)
    root.mainloop()
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
import threading
import os
import copy
import json

# Seus módulos
from gerador import calcular_simulacao
# Importamos as funções do json_utils
from json_utils import (
    salvar_config, carregar_config, 
    atualizar_estatisticas_json, 
    carregar_dados_tabelas, salvar_dados_tabelas,
    download_json_supabase, upload_json_supabase,
    FILE_RELACAO, FILE_DADOS
)
from pdf_processor import extrair_dados_pdf

# --- DESIGN SYSTEM ---
COLOR_BG = "#F9FAFB"
COLOR_CARD = "#FFFFFF"
COLOR_PRIMARY = "#2563EB"
COLOR_DANGER = "#DC2626"
COLOR_WARNING = "#F59E0B"
COLOR_SUCCESS = "#059669"
COLOR_TEXT_MAIN = "#111827"
COLOR_TEXT_SUB = "#6B7280"
COLOR_BORDER = "#E5E7EB"

class ConsorcioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador Recon Cloud & Local --> Dev Alessandro Uchoa")
        self.root.geometry("1000x750")
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
        self.notebook.add(self.tab_pdf, text=' Leitor PDF ')
        self.notebook.add(self.tab_relacao, text=' Relação Grupos ') 

        self.last_config = carregar_config()

        # Variáveis
        self.editor_data = {"metadata": [], "data": {}} 
        self.editor_backup = {"metadata": [], "data": {}}
        self.selected_table_id = None 
        
        self.relacao_data = {} 
        self.relacao_backup = {}
        self.relacao_vars_cache = {} 
        self.relacao_selected_grupo = None

        self.vars = {
            '2011': self.init_vars('2011'),
            '5121': self.init_vars('5121'),
            'esp': self.init_vars_especial(),
            'pdf': {'path': tk.StringVar()},
            'editor': {
                'id': tk.StringVar(), 'name': tk.StringVar(), 'category': tk.StringVar(),
                'plan': tk.StringVar(), 'adm': tk.DoubleVar(), 'fundo': tk.DoubleVar(), 'seguro': tk.DoubleVar()
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
        style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), background=COLOR_PRIMARY, foreground="white")
        style.map("Action.TButton", background=[("active", "#1D4ED8")])
        style.configure("Danger.TButton", font=("Segoe UI", 9, "bold"), background=COLOR_DANGER, foreground="white")
        style.map("Danger.TButton", background=[("active", "#991B1B")])
        style.configure("Warning.TButton", font=("Segoe UI", 9, "bold"), background=COLOR_WARNING, foreground="white")
        style.configure("Sec.TButton", font=("Segoe UI", 8), background="#E5E7EB", foreground=COLOR_TEXT_MAIN, borderwidth=0)
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
            'passo': tk.DoubleVar(value=saved.get('passo', defaults[4]))
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
            'apenas_csv': tk.BooleanVar(value=saved.get('apenas_csv', False))
        }

    def add_linha_compacta(self, parent, label_text, variable, row, col, tipo="texto", width=10):
        cell = ttk.Frame(parent, style="Main.TFrame")
        cell.grid(row=row, column=col, padx=5, pady=3, sticky='ew')
        ttk.Label(cell, text=label_text).pack(anchor='w')
        row_cont = ttk.Frame(cell, style="Main.TFrame")
        row_cont.pack(fill='x')
        if tipo == "moeda": ttk.Label(row_cont, text="R$", style="Sub.TLabel").pack(side='left', padx=(0,2))
        entry = ttk.Entry(row_cont, textvariable=variable, width=width)
        entry.pack(side='left', fill='x', expand=True)
        if tipo == "porcentagem": ttk.Label(row_cont, text=" %", style="Sub.TLabel").pack(side='left')

    # --- ABAS DE GERAÇÃO (EDITAR 2011/5121/CRIAR) ---
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
        
        # Botões de Ação (Frame para alinhar)
        btn_frame = ttk.Frame(content, style="Main.TFrame")
        btn_frame.pack(fill='x', pady=10)
        ttk.Button(btn_frame, text="💾 SALVAR LOCALMENTE (VALIDAR)", style="Sec.TButton", command=lambda: self.gerar_padrao_local(key)).pack(side='left', fill='x', expand=True, padx=(0, 5), ipady=5)
        ttk.Button(btn_frame, text="☁️ GERAR E ATUALIZAR NA NUVEM", style="Action.TButton", command=lambda: self.gerar_padrao(key)).pack(side='right', fill='x', expand=True, padx=(5, 0), ipady=5)

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
        for i, (t, v) in enumerate([("NORMAL (100%)", "N"), ("LIGHT (75%)", "L"), ("SUPERLIGHT (50%)", "SL")]):
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
        ttk.Checkbutton(bottom_frame, text="Tabela Apenas C/SV", variable=self.vars[key]['apenas_csv']).pack(side='left')
        
        # Botões de Ação
        btn_frame = ttk.Frame(content, style="Main.TFrame")
        btn_frame.pack(fill='x', pady=10)
        ttk.Button(btn_frame, text="💾 SALVAR LOCALMENTE", style="Sec.TButton", command=self.gerar_especial_local).pack(side='left', fill='x', expand=True, padx=(0, 5), ipady=5)
        ttk.Button(btn_frame, text="☁️ GERAR E ATUALIZAR NUVEM", style="Action.TButton", command=self.gerar_especial).pack(side='right', fill='x', expand=True, padx=(5, 0), ipady=5)

    # --- ABA EDITOR JSON ---
    def setup_tab_editor(self):
        content = ttk.Frame(self.tab_editor, style="Main.TFrame", padding=10)
        content.pack(fill='both', expand=True)
        top_bar = ttk.Frame(content, style="Main.TFrame")
        top_bar.pack(fill='x', pady=(0, 10))
        
        # Botões
        ttk.Button(top_bar, text="⬇️ Carregar Nuvem", style="Sec.TButton", command=self.editor_carregar_nuvem).pack(side='left', padx=(0, 5))
        self.lbl_editor_status = ttk.Label(top_bar, text="...", foreground=COLOR_TEXT_SUB)
        self.lbl_editor_status.pack(side='left', padx=5)
        
        # Grupo Salvar
        ttk.Button(top_bar, text="💾 Salvar Local", style="Sec.TButton", command=self.editor_salvar_local).pack(side='right', padx=(5, 0))
        ttk.Button(top_bar, text="⬆️ Salvar Nuvem", style="Action.TButton", command=self.editor_salvar_nuvem).pack(side='right', padx=(5, 0))
        ttk.Button(top_bar, text="↩ Desfazer", style="Warning.TButton", command=self.editor_reverter).pack(side='right')
        
        paned = tk.PanedWindow(content, orient=tk.HORIZONTAL, bg=COLOR_BG, sashwidth=4, showhandle=True)
        paned.pack(fill='both', expand=True)
        frame_list = ttk.Frame(paned, style="Main.TFrame")
        paned.add(frame_list, width=200)
        ttk.Label(frame_list, text="TABELAS (dados_consorcio)", font=("Segoe UI", 8, "bold"), foreground=COLOR_TEXT_SUB).pack(anchor='w', pady=(0, 5))
        scroll_lst = ttk.Scrollbar(frame_list)
        scroll_lst.pack(side='right', fill='y')
        self.lst_tabelas = tk.Listbox(frame_list, font=("Segoe UI", 9), borderwidth=1, relief="solid", yscrollcommand=scroll_lst.set)
        self.lst_tabelas.pack(side='left', fill='both', expand=True)
        scroll_lst.config(command=self.lst_tabelas.yview)
        self.lst_tabelas.bind('<<ListboxSelect>>', self.editor_selecionar_tabela)
        self.frame_edit = ttk.Frame(paned, style="Main.TFrame", padding=(10, 0, 0, 0))
        paned.add(self.frame_edit)
        # (Restante do Layout Editor Mantido Igual...)
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

    # --- Lógica Editor (CLOUD & LOCAL) ---
    def editor_carregar_nuvem(self):
        """Carrega dados_consorcio.json do Supabase"""
        self.lbl_editor_status.config(text="Baixando...", foreground=COLOR_WARNING)
        self.root.update()
        try:
            data = carregar_dados_tabelas() # Usa função do utils
            self.editor_data = data
            self.editor_backup = copy.deepcopy(data)
            self.lbl_editor_status.config(text=FILE_DADOS, foreground=COLOR_SUCCESS)
            self.editor_refresh_lista()
            self.tree_data.delete(*self.tree_data.get_children())
            self.selected_table_id = None
        except Exception as e:
            self.lbl_editor_status.config(text="Erro", foreground=COLOR_DANGER)
            messagebox.showerror("Erro Download", f"{e}")

    def editor_salvar_nuvem(self):
        """Salva todo o editor_data no Supabase"""
        self.lbl_editor_status.config(text="Enviando...", foreground=COLOR_WARNING)
        self.root.update()
        try:
            upload_json_supabase(FILE_DADOS, self.editor_data) # Sobrescreve
            self.editor_backup = copy.deepcopy(self.editor_data)
            self.lbl_editor_status.config(text="Salvo!", foreground=COLOR_SUCCESS)
            messagebox.showinfo("Sucesso", "Dados atualizados na nuvem!")
        except Exception as e:
            self.lbl_editor_status.config(text="Erro", foreground=COLOR_DANGER)
            messagebox.showerror("Erro Upload", f"{e}")

    def editor_salvar_local(self):
        """Salva o estado atual do Editor em um arquivo local"""
        path = filedialog.asksaveasfilename(title="Salvar JSON Local", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="dados_consorcio_backup.json")
        if not path: return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.editor_data, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Salvo", f"Arquivo salvo localmente em:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # (Métodos auxiliares do editor mantidos iguais...)
    def editor_refresh_lista(self):
        self.lst_tabelas.delete(0, tk.END)
        if not self.editor_data: return
        if "metadata" in self.editor_data:
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
            parent_id = self.tree_data.insert("", "end", iid=f"c_{i}", text=cred_fmt, values=("Expandir",), open=False)
            prazos = r.get('prazos', [])
            prazos.sort(key=lambda x: x.get('prazo', 0))
            for j, p in enumerate(prazos):
                prazo_meses = p.get('prazo', 0)
                val_unico = p.get('parcela', None)
                val_csv = p.get('parcela_CSV', 0)
                val_ssv = p.get('parcela_SSV', None)
                if val_unico is not None: detalhe = f"P: R$ {val_unico:.2f}"
                else:
                    detalhe = f"CSV: {val_csv:.2f}"
                    if val_ssv is not None: detalhe += f" | SSV: {val_ssv:.2f}"
                self.tree_data.insert(parent_id, "end", iid=f"p_{i}_{j}", text=f"{prazo_meses}m", values=(detalhe,))

    def editor_atualizar_metadados(self):
        if not self.selected_table_id: return
        for m in self.editor_data["metadata"]:
            if m["id"] == self.selected_table_id:
                m["name"] = self.vars['editor']['name'].get()
                m["category"] = self.vars['editor']['category'].get()
                m["plan"] = self.vars['editor']['plan'].get()
                m["taxaAdmin"] = self.vars['editor']['adm'].get()
                m["seguroPct"] = self.vars['editor']['seguro'].get()
                messagebox.showinfo("OK", "Meta atualizado (Memória). Salve na Nuvem.")
                return

    def editor_converter_seguro(self):
        t_id = self.selected_table_id
        if not t_id: return
        rows = self.editor_data["data"].get(t_id, [])
        alteracoes = 0
        for r in rows:
            for p in r.get('prazos', []):
                if 'parcela_SSV' in p or ('parcela_CSV' in p and 'parcela' not in p):
                    if 'parcela_SSV' in p: del p['parcela_SSV']
                    if 'parcela_CSV' in p: val = p.pop('parcela_CSV'); p['parcela'] = val
                    alteracoes += 1
        if alteracoes > 0:
            self.editor_selecionar_tabela(None)
            messagebox.showinfo("OK", f"{alteracoes} convertidos.")
        else: messagebox.showinfo("Aviso", "Nada alterado.")

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
        if t_id not in self.editor_data["data"]: return
        rows = self.editor_data["data"][t_id]
        if item_id.startswith("c_"):
            idx_cred = int(item_id.split("_")[1])
            if not messagebox.askyesno("Excluir", "Deseja excluir TODO o crédito?"): return
            del rows[idx_cred]
            self.editor_data["data"][t_id] = rows
            self.editor_selecionar_tabela(None)
        elif item_id.startswith("p_"):
            parts = item_id.split("_")
            idx_cred = int(parts[1])
            idx_prazo = int(parts[2])
            cred_row = rows[idx_cred]
            prazos = cred_row.get('prazos', [])
            if len(prazos) <= 1:
                if messagebox.askyesno("Aviso Crítico", "Único prazo. Excluir crédito inteiro?"): del rows[idx_cred]
                else: return
            else:
                if not messagebox.askyesno("Confirmar", "Excluir apenas esta opção?"): return
                del rows[idx_cred]['prazos'][idx_prazo]
            self.editor_data["data"][t_id] = rows
            self.editor_selecionar_tabela(None)

    def editor_reverter(self):
        if not self.editor_backup: return
        if messagebox.askyesno("Reverter", "Desfazer alterações locais?"): 
            self.editor_data = copy.deepcopy(self.editor_backup)
            self.editor_refresh_lista(); self.tree_data.delete(*self.tree_data.get_children()); self.selected_table_id = None

    # --- ABA PDF (CLOUD & LOCAL) ---
    def setup_tab_pdf(self):
        content = ttk.Frame(self.tab_pdf, style="Main.TFrame", padding=15)
        content.pack(fill='both', expand=True)
        # Seleção de PDF (Local)
        lf_sel = ttk.LabelFrame(content, text="ARQUIVO LOCAL (PDF)", style="Card.TLabelframe", padding=10)
        lf_sel.pack(fill='x', pady=(0, 10))
        row_file = ttk.Frame(lf_sel, style="Main.TFrame")
        row_file.pack(fill='x')
        ttk.Button(row_file, text="📁 Selecionar PDF...", style="Sec.TButton", command=self.selecionar_pdf).pack(side='left', padx=(0, 10))
        lbl_path = ttk.Label(row_file, textvariable=self.vars['pdf']['path'], foreground=COLOR_TEXT_SUB, width=40)
        lbl_path.pack(side='left', fill='x', expand=True)
        
        # Ações
        ttk.Button(content, text="💾 EXTRAIR E SALVAR LOCALMENTE", style="Sec.TButton", command=self.executar_processamento_pdf_local).pack(fill='x', pady=(10, 5), ipady=5)
        ttk.Button(content, text="☁️ EXTRAIR E ATUALIZAR NUVEM", style="Action.TButton", command=self.executar_processamento_pdf).pack(fill='x', pady=5, ipady=6)
        
        # Log
        lf_log = ttk.LabelFrame(content, text="LOG", style="Card.TLabelframe", padding=5)
        lf_log.pack(fill='both', expand=True)
        self.txt_log = scrolledtext.ScrolledText(lf_log, height=10, font=("Consolas", 8), state='disabled', bg="#F3F4F6", relief="flat")
        self.txt_log.pack(fill='both', expand=True)

    def log_pdf(self, message):
        self.txt_log.config(state='normal'); self.txt_log.insert(tk.END, message + "\n"); self.txt_log.see(tk.END); self.txt_log.config(state='disabled'); self.root.update_idletasks() 

    def selecionar_pdf(self):
        path = filedialog.askopenfilename(title="Selecione o PDF", filetypes=[("PDF", "*.pdf")])
        if path: self.vars['pdf']['path'].set(path); self.txt_log.config(state='normal'); self.txt_log.delete(1.0, tk.END); self.txt_log.config(state='disabled'); self.log_pdf(f"Arquivo: {os.path.basename(path)}")

    def executar_processamento_pdf(self):
        pdf_path = self.vars['pdf']['path'].get()
        if not pdf_path or not os.path.exists(pdf_path): messagebox.showwarning("Atenção", "Selecione um PDF."); return
        threading.Thread(target=self._thread_pdf_cloud, args=(pdf_path,)).start()

    def executar_processamento_pdf_local(self):
        pdf_path = self.vars['pdf']['path'].get()
        if not pdf_path or not os.path.exists(pdf_path): messagebox.showwarning("Atenção", "Selecione um PDF."); return
        threading.Thread(target=self._thread_pdf_local, args=(pdf_path,)).start()

    def _thread_pdf_cloud(self, pdf_path):
        self.log_pdf("Extraindo dados do PDF...")
        dados = extrair_dados_pdf(pdf_path, callback_log=self.log_pdf)
        if not dados: self.log_pdf("❌ Falha na extração."); return
        self.log_pdf(f"✅ {len(dados)} grupos encontrados. Baixando Nuvem...")
        try:
            novos, atualizados = atualizar_estatisticas_json(dados)
            self.log_pdf(f"RESULTADO: +{novos} Novos | ⟳{atualizados} Atualizados")
            self.log_pdf(f"Enviado para: {FILE_RELACAO} (Supabase)")
            messagebox.showinfo("Concluído", f"Nuvem Atualizada!\nNovos: {novos}\nAtualizados: {atualizados}")
        except Exception as e: self.log_pdf(f"❌ Erro Supabase: {str(e)}")

    def _thread_pdf_local(self, pdf_path):
        self.log_pdf("Extraindo dados do PDF (Modo Local)...")
        dados = extrair_dados_pdf(pdf_path, callback_log=self.log_pdf)
        if not dados: self.log_pdf("❌ Falha na extração."); return
        
        path_save = filedialog.asksaveasfilename(title="Salvar Extração Local", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="estatisticas_extraidas.json")
        if not path_save: self.log_pdf("Operação cancelada."); return

        try:
            with open(path_save, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=4, ensure_ascii=False)
            self.log_pdf(f"💾 Salvo em: {path_save}")
            messagebox.showinfo("Sucesso", "Dados extraídos e salvos localmente!")
        except Exception as e:
            self.log_pdf(f"❌ Erro ao salvar: {e}")

    # --- ABA RELAÇÃO (CLOUD & LOCAL) ---
    def setup_tab_relacao(self):
        content = ttk.Frame(self.tab_relacao, style="Main.TFrame", padding=10)
        content.pack(fill='both', expand=True)
        top_bar = ttk.Frame(content, style="Main.TFrame")
        top_bar.pack(fill='x', pady=(0, 10))
        # Botões
        ttk.Button(top_bar, text="⬇️ Carregar Nuvem", style="Sec.TButton", command=self.relacao_carregar_nuvem).pack(side='left', padx=(0, 5))
        self.lbl_relacao_status = ttk.Label(top_bar, text="...", foreground=COLOR_TEXT_SUB)
        self.lbl_relacao_status.pack(side='left', padx=5)
        
        ttk.Button(top_bar, text="💾 Salvar Local", style="Sec.TButton", command=self.relacao_salvar_local).pack(side='right', padx=(5, 0))
        ttk.Button(top_bar, text="⬆️ Salvar Nuvem", style="Action.TButton", command=self.relacao_salvar_nuvem).pack(side='right', padx=(5, 0))
        ttk.Button(top_bar, text="↩ Desfazer", style="Warning.TButton", command=self.relacao_reverter).pack(side='right')

        paned = tk.PanedWindow(content, orient=tk.HORIZONTAL, bg=COLOR_BG, sashwidth=4, showhandle=True)
        paned.pack(fill='both', expand=True)
        frame_list = ttk.Frame(paned, style="Main.TFrame")
        paned.add(frame_list, width=220)
        btn_grp_frame = ttk.Frame(frame_list, style="Main.TFrame")
        btn_grp_frame.pack(fill='x', pady=(0, 5))
        ttk.Button(btn_grp_frame, text="➕ Novo Grp", style="Sec.TButton", command=self.relacao_novo_grupo).pack(side='left', fill='x', expand=True, padx=(0,2))
        ttk.Button(btn_grp_frame, text="🗑️ Del Grp", style="Danger.TButton", command=self.relacao_excluir_grupo).pack(side='right', fill='x', expand=True, padx=(2,0))
        scroll_lst = ttk.Scrollbar(frame_list)
        scroll_lst.pack(side='right', fill='y')
        self.lst_grupos = tk.Listbox(frame_list, font=("Segoe UI", 9), borderwidth=1, relief="solid", yscrollcommand=scroll_lst.set)
        self.lst_grupos.pack(side='left', fill='both', expand=True)
        scroll_lst.config(command=self.lst_grupos.yview)
        self.lst_grupos.bind('<<ListboxSelect>>', self.relacao_selecionar_grupo)
        right_panel = ttk.Frame(paned, style="Main.TFrame", padding=(10, 0, 0, 0))
        paned.add(right_panel)
        # (Toolbar e Canvas mantidos iguais)
        toolbar_fields = ttk.LabelFrame(right_panel, text="Campos", style="Card.TLabelframe", padding=5)
        toolbar_fields.pack(fill='x', pady=(0, 5))
        ttk.Button(toolbar_fields, text="➕ Add Global", style="Sec.TButton", command=self.relacao_add_global_field).pack(side='left', padx=(0, 5))
        ttk.Button(toolbar_fields, text="➖ Del Global", style="Warning.TButton", command=self.relacao_del_global_field).pack(side='right', padx=(5, 0))
        ttk.Button(toolbar_fields, text="➖ Del Local", style="Sec.TButton", command=self.relacao_del_local_field).pack(side='right')
        self.canvas_relacao = tk.Canvas(right_panel, bg=COLOR_BG, highlightthickness=0)
        scroll_y = ttk.Scrollbar(right_panel, orient="vertical", command=self.canvas_relacao.yview)
        self.frame_dynamic_fields = ttk.Frame(self.canvas_relacao, style="Main.TFrame")
        self.frame_dynamic_fields.bind("<Configure>", lambda e: self.canvas_relacao.configure(scrollregion=self.canvas_relacao.bbox("all")))
        self.canvas_relacao.create_window((0, 0), window=self.frame_dynamic_fields, anchor="nw")
        self.canvas_relacao.configure(yscrollcommand=scroll_y.set)
        self.canvas_relacao.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

    # --- Lógica Relação (CLOUD & LOCAL) ---
    def relacao_carregar_nuvem(self):
        self.lbl_relacao_status.config(text="Baixando...", foreground=COLOR_WARNING)
        self.root.update()
        try:
            raw_list = download_json_supabase(FILE_RELACAO)
            self.relacao_data = {}
            for item in raw_list:
                gid = str(item.get("Grupo", "S/N"))
                self.relacao_data[gid] = item
            self.relacao_backup = copy.deepcopy(self.relacao_data)
            self.lbl_relacao_status.config(text=FILE_RELACAO, foreground=COLOR_SUCCESS)
            self.relacao_refresh_list()
            self.relacao_limpar_painel()
        except Exception as e:
            self.lbl_relacao_status.config(text="Erro", foreground=COLOR_DANGER)
            messagebox.showerror("Erro Download", f"{e}")

    def relacao_salvar_nuvem(self):
        self.relacao_atualizar_memoria()
        erros = []
        for grp, dados in self.relacao_data.items():
            for k, v in dados.items():
                if v is None or str(v).strip() == "": erros.append(f"Grupo {grp} -> Campo '{k}' vazio.")
        if erros:
            messagebox.showerror("Erro Validação", "\n".join(erros[:5]))
            return

        self.lbl_relacao_status.config(text="Enviando...", foreground=COLOR_WARNING)
        self.root.update()
        try:
            final_list = list(self.relacao_data.values())
            try: final_list.sort(key=lambda x: int(x.get("Grupo", 0)))
            except: pass
            upload_json_supabase(FILE_RELACAO, final_list) # Sobrescreve
            self.relacao_backup = copy.deepcopy(self.relacao_data)
            self.lbl_relacao_status.config(text="Salvo!", foreground=COLOR_SUCCESS)
            messagebox.showinfo("Sucesso", "Relação salva na nuvem!")
        except Exception as e:
            self.lbl_relacao_status.config(text="Erro", foreground=COLOR_DANGER)
            messagebox.showerror("Erro Upload", f"{e}")

    def relacao_salvar_local(self):
        """Salva a lista de grupos atual em um arquivo local"""
        self.relacao_atualizar_memoria()
        path = filedialog.asksaveasfilename(title="Salvar Relação Local", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="relacao_grupos_backup.json")
        if not path: return
        try:
            final_list = list(self.relacao_data.values())
            try: final_list.sort(key=lambda x: int(x.get("Grupo", 0)))
            except: pass
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(final_list, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Salvo", f"Arquivo salvo localmente em:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # (Métodos auxiliares de relação mantidos...)
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
                if k == "Grupo" or k == "Prazo Máximo":
                    try: val = int(val)
                    except: pass
                self.relacao_data[self.relacao_selected_grupo][k] = val

    def _renderizar_campos_grupo(self, grp_id):
        for widget in self.frame_dynamic_fields.winfo_children(): widget.destroy()
        self.relacao_vars_cache = {}
        dados = self.relacao_data.get(grp_id, {})
        ttk.Label(self.frame_dynamic_fields, text=f"Editando Grupo: {grp_id}", font=("Segoe UI", 10, "bold"), foreground=COLOR_PRIMARY).pack(anchor='w', pady=(0, 10))
        for key, val in dados.items():
            f = ttk.Frame(self.frame_dynamic_fields, style="Main.TFrame")
            f.pack(fill='x', pady=2)
            ttk.Label(f, text=key, width=20).pack(side='left')
            var = tk.StringVar(value=str(val))
            self.relacao_vars_cache[key] = var
            entry = ttk.Entry(f, textvariable=var)
            if key == "Grupo": entry.config(state='readonly') 
            entry.pack(side='left', fill='x', expand=True)

    def relacao_selecionar_grupo(self, event):
        sel = self.lst_grupos.curselection()
        if not sel: return
        self.relacao_atualizar_memoria() 
        grp_id = self.lst_grupos.get(sel[0])
        self.relacao_selected_grupo = grp_id
        self._renderizar_campos_grupo(grp_id)

    def relacao_novo_grupo(self):
        if not self.relacao_data: messagebox.showwarning("Aviso", "Carregue a nuvem primeiro."); return
        new_id = simpledialog.askstring("Novo Grupo", "Número:")
        if not new_id: return
        if new_id in self.relacao_data: messagebox.showerror("Erro", "Já existe."); return
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

    def relacao_excluir_grupo(self):
        sel = self.lst_grupos.curselection()
        if not sel: return
        grp_id = self.lst_grupos.get(sel[0])
        if messagebox.askyesno("Excluir", f"Apagar {grp_id}?"):
            if grp_id == self.relacao_selected_grupo: self.relacao_limpar_painel()
            del self.relacao_data[grp_id]
            self.relacao_refresh_list()

    def relacao_add_global_field(self):
        if not self.relacao_data: return
        field_name = simpledialog.askstring("Novo Campo", "Nome da Chave:")
        if not field_name: return
        for grp in self.relacao_data:
            if field_name not in self.relacao_data[grp]: self.relacao_data[grp][field_name] = ""
        if self.relacao_selected_grupo: self.lst_grupos.event_generate("<<ListboxSelect>>")

    def relacao_del_global_field(self):
        if not self.relacao_data: return
        self.relacao_atualizar_memoria()
        field_name = simpledialog.askstring("Excluir Global", "Nome da Chave:")
        if not field_name: return
        if field_name == "Grupo": return
        count = 0
        for grp in self.relacao_data:
            if field_name in self.relacao_data[grp]:
                del self.relacao_data[grp][field_name]; count += 1
        if count > 0:
            if self.relacao_selected_grupo: self._renderizar_campos_grupo(self.relacao_selected_grupo)
            messagebox.showinfo("Info", f"Removido de {count}.")

    def relacao_del_local_field(self):
        if not self.relacao_selected_grupo: return
        self.relacao_atualizar_memoria()
        field_name = simpledialog.askstring("Excluir Local", "Nome da Chave:")
        if not field_name: return
        if field_name == "Grupo": return
        dados = self.relacao_data[self.relacao_selected_grupo]
        if field_name in dados:
            del self.relacao_data[self.relacao_selected_grupo][field_name]
            self._renderizar_campos_grupo(self.relacao_selected_grupo)

    def relacao_reverter(self):
        if not self.relacao_backup: return
        if messagebox.askyesno("Desfazer", "Reverter para o estado da nuvem?"):
            self.relacao_data = copy.deepcopy(self.relacao_backup)
            self.relacao_refresh_list()
            self.relacao_limpar_painel()

    # --- GERADOR (CLOUD & LOCAL) ---
    def salvar_estado_atual(self):
        dados = {k: {sk: sv.get() for sk, sv in v.items()} for k, v in self.vars.items() if k not in ['pdf','editor']}
        salvar_config(dados)
    
    def gerar_padrao(self, grupo):
        self.salvar_estado_atual() 
        d = self.vars[grupo]
        pl = d['plano'].get()
        chave = f"t_{('imovel' if grupo=='2011' else 'auto')}{grupo}_{('normal' if pl=='N' else pl)}"
        try:
            res = calcular_simulacao(grupo, pl, d['prazo'].get(), d['credito_ini'].get(), d['credito_fim'].get(), d['passo'].get())
            salvar_dados_tabelas(chave, res)
            messagebox.showinfo("Sucesso", f"Tabela {chave} atualizada no Supabase!")
        except Exception as e: messagebox.showerror("Erro Crítico", f"Falha ao gerar/upload:\n{str(e)}")

    def gerar_padrao_local(self, grupo):
        self.salvar_estado_atual() 
        d = self.vars[grupo]
        pl = d['plano'].get()
        chave = f"t_{('imovel' if grupo=='2011' else 'auto')}{grupo}_{('normal' if pl=='N' else pl)}"
        path = filedialog.asksaveasfilename(title=f"Salvar {chave} Local", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile=f"{chave}.json")
        if not path: return
        try:
            res = calcular_simulacao(grupo, pl, d['prazo'].get(), d['credito_ini'].get(), d['credito_fim'].get(), d['passo'].get())
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(res, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Salvo", f"Tabela {chave} salva localmente!")
        except Exception as e: messagebox.showerror("Erro Crítico", f"{str(e)}")

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
            if d['apenas_csv'].get():
                for item in res:
                    for p in item['prazos']:
                        if 'parcela_SSV' in p: del p['parcela_SSV']
                        if 'parcela_CSV' in p: p['parcela'] = p.pop('parcela_CSV')
            salvar_dados_tabelas(chave, res, metadata_item=meta)
            messagebox.showinfo("Sucesso", f"Tabela Especial {chave} atualizada no Supabase!")
        except Exception as e: messagebox.showerror("Erro Crítico", f"Falha ao gerar/upload:\n{str(e)}")

    def gerar_especial_local(self):
        self.salvar_estado_atual()
        d = self.vars['esp']
        path = filedialog.asksaveasfilename(title=f"Salvar Especial Local", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile=f"tabela_especial.json")
        if not path: return
        pl = d['plano_tipo'].get()
        seg = d['seguro'].get()
        try:
            res = calcular_simulacao("ESPECIAL", "CUSTOM", d['prazo'].get(), d['credito_ini'].get(), d['credito_fim'].get(), d['passo'].get(), custom_data={'fator': {"N":1.0,"L":0.75,"SL":0.5}[pl], 'adm': d['adm'].get()/100, 'fundo': 0.03, 'seguro': seg/100})
            if d['apenas_csv'].get():
                for item in res:
                    for p in item['prazos']:
                        if 'parcela_SSV' in p: del p['parcela_SSV']
                        if 'parcela_CSV' in p: p['parcela'] = p.pop('parcela_CSV')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(res, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Salvo", f"Tabela especial salva localmente!")
        except Exception as e: messagebox.showerror("Erro Crítico", f"{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConsorcioApp(root)
    root.mainloop()
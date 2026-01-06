import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
import threading
import os
import copy
import json
from datetime import datetime  

from gerador import calcular_simulacao
from json_utils import (
    salvar_config, carregar_config, 
    atualizar_estatisticas_json, 
    atualizar_historico_assembleias, 
    carregar_dados_tabelas, salvar_dados_tabelas,
    download_json_supabase, upload_json_supabase,
    FILE_RELACAO, FILE_DADOS, FILE_HISTORICO
)
from pdf_processor import extrair_dados_pdf
from login import LoginWindow 
from auth import AuthManager

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

# --- CONSTANTES DE ARQUIVOS ---
FILE_MESSAGES = "mensagem_rolante_editavel.json"
FILE_LOGS = "historico_global_logs.json" 

class ConsorcioApp:
    def __init__(self, root, current_user_role="user", current_username="Usuario"): 
        self.root = root
        self.role = current_user_role 
        self.username = current_username 
        
        role_label = " (ADMINISTRADOR)" if self.role == "admin" else " "
        self.root.title(f" Gerenciador de Banco de Dados - Simulador Recon {role_label} | Logado como: {self.username}")
        self.root.geometry("690x670")
        self.root.configure(bg=COLOR_BG)
        
        self.setup_styles()
        self.auth = AuthManager()

        # --- MENU SUPERIOR (APENAS SE FOR ADMIN) ---
        if self.role == "admin":
            menubar = tk.Menu(root)
            root.config(menu=menubar)

            menu_admin = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Administração 🔒", menu=menu_admin)
            
            # --- NOVAS OPÇÕES ---
            menu_admin.add_command(label="📜 Consultar Logs Globais", command=self.abrir_janela_logs) # <--- NOVO
            menu_admin.add_separator()
            # --------------------
            
            menu_admin.add_command(label="➕ Cadastrar Usuário", command=self.abrir_janela_cadastro)
            menu_admin.add_command(label="🔄 Resetar Senha (Padrão)", command=self.abrir_janela_reset)
            menu_admin.add_command(label="❌ Bloquear Usuário", command=self.abrir_janela_exclusao)
            menu_admin.add_separator()
            menu_admin.add_command(label="Sair", command=root.quit)
        # -------------------------------------------

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)

        self.tab_2011 = ttk.Frame(self.notebook, style="Main.TFrame")
        self.tab_5121 = ttk.Frame(self.notebook, style="Main.TFrame")
        self.tab_especial = ttk.Frame(self.notebook, style="Main.TFrame")
        self.tab_editor = ttk.Frame(self.notebook, style="Main.TFrame")
        self.tab_pdf = ttk.Frame(self.notebook, style="Main.TFrame")
        self.tab_relacao = ttk.Frame(self.notebook, style="Main.TFrame")
        self.tab_mensagens = ttk.Frame(self.notebook, style="Main.TFrame") 

        self.notebook.add(self.tab_2011, text=' Editar 2011 ')
        self.notebook.add(self.tab_5121, text=' Editar 5121 ')
        self.notebook.add(self.tab_especial, text=' Criar Tabela ')
        self.notebook.add(self.tab_editor, text=' Editar Tabelas ')
        self.notebook.add(self.tab_pdf, text=' Leitor PDF das Assembleias ')
        self.notebook.add(self.tab_relacao, text=' Relação de Grupos ')
        self.notebook.add(self.tab_mensagens, text=' Informativos ') 

        self.last_config = carregar_config()

        # Variáveis
        self.editor_data = {"metadata": [], "data": {}} 
        self.editor_backup = {"metadata": [], "data": {}}
        self.selected_table_id = None 
        
        self.relacao_data = {} 
        self.relacao_backup = {}
        self.relacao_vars_cache = {} 
        self.relacao_selected_grupo = None

        # Variáveis Mensagens
        self.messages_data = {"messages": [], "lastUpdate": ""}
        self.msg_selected_index = None

        self.vars = {
            '2011': self.init_vars('2011'),
            '5121': self.init_vars('5121'),
            'esp': self.init_vars_especial(),
            'pdf': {'path': tk.StringVar()},
            'editor': {
                'id': tk.StringVar(), 'name': tk.StringVar(), 'category': tk.StringVar(),
                'plan': tk.StringVar(), 'adm': tk.DoubleVar(), 'fundo': tk.DoubleVar(), 'seguro': tk.DoubleVar()
            },
            'msg': {'input': tk.StringVar()}
        }

        self.setup_tab_padrao(self.tab_2011, "2011", ["Normal", "Light", "SuperLight"], ["N", "L", "SL"])
        self.setup_tab_padrao(self.tab_5121, "5121", ["Normal", "Light"], ["N", "L"])
        self.setup_tab_especial()
        self.setup_tab_editor()
        self.setup_tab_pdf()
        self.setup_tab_relacao()
        self.setup_tab_mensagens() 

    # --- SISTEMA DE LOG GLOBAL (NUVEM + LOCAL) ---
    def _registrar_log(self, acao, detalhes):
        """Salva log e sincroniza com a nuvem em background"""
        registro = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "usuario": self.username,
            "cargo": self.role,
            "acao": acao,
            "detalhes": detalhes
        }

        def _sync_log_background():
            lista_logs = []
            
            # 1. Tenta baixar da nuvem primeiro
            try:
                dados_cloud = download_json_supabase(FILE_LOGS)
                if isinstance(dados_cloud, list):
                    lista_logs = dados_cloud
            except Exception as e:
                print(f"[LOG] Falha ao baixar logs da nuvem (usando local): {e}")
                if os.path.exists(FILE_LOGS):
                    try:
                        with open(FILE_LOGS, 'r', encoding='utf-8') as f:
                            lista_logs = json.load(f)
                    except:
                        lista_logs = []

            # 2. Adiciona o novo registro
            lista_logs.append(registro)
            
            # 3. Salva Localmente
            try:
                with open(FILE_LOGS, 'w', encoding='utf-8') as f:
                    json.dump(lista_logs, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"[LOG] Erro ao salvar log local: {e}")

            # 4. Envia para a Nuvem
            try:
                upload_json_supabase(FILE_LOGS, lista_logs)
                print(f"[LOG] Sincronizado com a nuvem: {acao}")
            except Exception as e:
                print(f"[LOG] Erro ao subir log para nuvem: {e}")

        threading.Thread(target=_sync_log_background, daemon=True).start()

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
        defaults = ('N', 201, 200000.0, 300000.0, 10000.0) if tipo == '2011' else ('N', 106, 80000.0, 110000.0, 10000.0)
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
            'id_tabela': tk.StringVar(value=saved.get('id_tabela', "nomedatabela")), 
            'nome_real': tk.StringVar(value=saved.get('nome_real', "Insira o nome da tabela aqui")), 
            'plano_tipo': tk.StringVar(value=saved.get('plano_tipo', "N")), 
            'adm': tk.DoubleVar(value=saved.get('adm', 25.0)),
            'seguro': tk.DoubleVar(value=saved.get('seguro', 0.059)),
            'prazo': tk.IntVar(value=saved.get('prazo', 201)),
            'credito_ini': tk.DoubleVar(value=saved.get('credito_ini', 200000)),
            'credito_fim': tk.DoubleVar(value=saved.get('credito_fim', 300000)),
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

    # --- ADMINISTRAÇÃO: CONSULTA DE LOGS (NOVO) ---
    def abrir_janela_logs(self):
        top = tk.Toplevel(self.root)
        top.title("Logs Globais do Sistema (Nuvem)")
        top.geometry("900x500")
        top.configure(bg=COLOR_BG)
        
        # Centralizar
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 450
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 250
        top.geometry(f"+{x}+{y}")

        # Topo
        frame_top = ttk.Frame(top, style="Main.TFrame", padding=10)
        frame_top.pack(fill='x')
        ttk.Label(frame_top, text="Histórico de Atividades", font=("Segoe UI", 12, "bold"), background=COLOR_BG).pack(side='left')
        
        lbl_status = ttk.Label(frame_top, text="Aguardando...", foreground=COLOR_TEXT_SUB, background=COLOR_BG)
        lbl_status.pack(side='right', padx=10)

        # Tabela
        cols = ("Data/Hora", "Usuário", "Cargo", "Ação", "Detalhes")
        tree = ttk.Treeview(top, columns=cols, show='headings', selectmode='browse')
        
        tree.heading("Data/Hora", text="Data/Hora")
        tree.heading("Usuário", text="Usuário")
        tree.heading("Cargo", text="Cargo")
        tree.heading("Ação", text="Ação")
        tree.heading("Detalhes", text="Detalhes")
        
        tree.column("Data/Hora", width=130, anchor="center")
        tree.column("Usuário", width=100, anchor="center")
        tree.column("Cargo", width=60, anchor="center")
        tree.column("Ação", width=150)
        tree.column("Detalhes", width=400)

        # Scrollbar
        scroll_y = ttk.Scrollbar(top, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll_y.set)
        
        tree.pack(side='left', fill='both', expand=True, padx=(10,0), pady=10)
        scroll_y.pack(side='right', fill='y', pady=10, padx=(0,10))

        # Botão Atualizar
        btn_refresh = ttk.Button(frame_top, text="🔄 Atualizar Agora", style="Action.TButton")
        btn_refresh.pack(side='right')

        def carregar_dados():
            lbl_status.config(text="Baixando da nuvem...", foreground=COLOR_WARNING)
            btn_refresh.config(state='disabled')
            
            # Limpa tabela
            for i in tree.get_children(): tree.delete(i)

            def _thread_fetch():
                try:
                    # Baixa do Supabase
                    dados = download_json_supabase(FILE_LOGS)
                    if not dados or not isinstance(dados, list):
                        dados = []
                    
                    # Ordena do mais recente para o mais antigo
                    try:
                        dados.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                    except: pass
                    
                    def _update_ui():
                        for item in dados:
                            tree.insert("", "end", values=(
                                item.get("timestamp", ""),
                                item.get("usuario", ""),
                                item.get("cargo", ""),
                                item.get("acao", ""),
                                item.get("detalhes", "")
                            ))
                        lbl_status.config(text=f"{len(dados)} registros carregados.", foreground=COLOR_SUCCESS)
                        btn_refresh.config(state='normal')
                    
                    top.after(0, _update_ui)
                    
                except Exception as e:
                    def _error_ui():
                        lbl_status.config(text="Erro ao baixar.", foreground=COLOR_DANGER)
                        messagebox.showerror("Erro", f"Falha ao buscar logs: {e}", parent=top)
                        btn_refresh.config(state='normal')
                    top.after(0, _error_ui)

            threading.Thread(target=_thread_fetch, daemon=True).start()

        btn_refresh.config(command=carregar_dados)
        
        # Carrega automaticamente ao abrir
        carregar_dados()

    # --- ADMINISTRAÇÃO: CADASTRO COM ROLE ---
    def abrir_janela_cadastro(self):
        top = tk.Toplevel(self.root)
        top.title("Novo Usuário")
        top.geometry("300x320")
        top.configure(bg=COLOR_BG)
        top.resizable(False, False)
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 150
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 160
        top.geometry(f"+{x}+{y}")

        ttk.Label(top, text="Criar Acesso", font=("Segoe UI", 12, "bold"), background=COLOR_BG).pack(pady=10)

        frame_form = ttk.Frame(top, style="Main.TFrame")
        frame_form.pack(padx=20, pady=5, fill='x')

        ttk.Label(frame_form, text="Usuário:").pack(anchor='w')
        entry_user = ttk.Entry(frame_form)
        entry_user.pack(fill='x', pady=(0, 5))

        ttk.Label(frame_form, text="Senha:").pack(anchor='w')
        entry_pass = ttk.Entry(frame_form, show="*")
        entry_pass.pack(fill='x', pady=(0, 5))

        ttk.Label(frame_form, text="Confirmar:").pack(anchor='w')
        entry_conf = ttk.Entry(frame_form, show="*")
        entry_conf.pack(fill='x', pady=(0, 10))

        # --- SELETOR DE CARGO ---
        ttk.Label(frame_form, text="Tipo de Permissão:").pack(anchor='w')
        role_var = tk.StringVar(value="user")
        frame_radio = ttk.Frame(frame_form, style="Main.TFrame")
        frame_radio.pack(fill='x', pady=5)
        ttk.Radiobutton(frame_radio, text="Vendedor (Comum)", variable=role_var, value="user").pack(anchor='w')
        ttk.Radiobutton(frame_radio, text="ADMINISTRADOR", variable=role_var, value="admin").pack(anchor='w')
        # ------------------------

        def salvar_novo():
            u, p, c = entry_user.get().strip(), entry_pass.get().strip(), entry_conf.get().strip()
            role = role_var.get()

            if not u or not p: return messagebox.showwarning("Atenção", "Preencha tudo.", parent=top)
            if p != c: return messagebox.showerror("Erro", "Senhas não conferem.", parent=top)

            sucesso, msg = self.auth.create_user(u, p, role=role) 
            
            if sucesso:
                self._registrar_log("ADMIN_CRIAR_USUARIO", f"Usuário criado: {u} | Permissão: {role}")
                messagebox.showinfo("Sucesso", f"Usuário '{u}' ({role}) criado!", parent=top)
                top.destroy()
            else:
                messagebox.showerror("Erro", msg, parent=top)

        ttk.Button(top, text="SALVAR", style="Action.TButton", command=salvar_novo).pack(fill='x', padx=20, pady=10)

    # --- ADMINISTRAÇÃO: RESET DE SENHA ---
    def abrir_janela_reset(self):
        top = tk.Toplevel(self.root)
        top.title("Resetar Senha")
        top.geometry("300x350")
        top.configure(bg=COLOR_BG)
        
        # Centralizar
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 150
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 175
        top.geometry(f"+{x}+{y}")

        ttk.Label(top, text="Resetar p/ Padrão '12345'", font=("Segoe UI", 10, "bold"), background=COLOR_BG).pack(pady=10)

        frame_list = ttk.Frame(top, style="Main.TFrame")
        frame_list.pack(fill='both', expand=True, padx=20, pady=5)
        
        lst_users = tk.Listbox(frame_list, height=10)
        lst_users.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(frame_list, orient="vertical", command=lst_users.yview)
        scrollbar.pack(side='right', fill='y')
        lst_users.config(yscrollcommand=scrollbar.set)

        users = self.auth.get_users_list()
        for u in users:
            lst_users.insert(tk.END, u)

        def confirmar_reset():
            sel = lst_users.curselection()
            if not sel: return
            usuario = lst_users.get(sel[0])
            
            if messagebox.askyesno("Confirmar Reset", 
                                   f"A senha de '{usuario}' voltará para '12345'.\n"
                                   f"Ele será obrigado a trocá-la no próximo login.\n\n"
                                   "Deseja continuar?", parent=top):
                
                sucesso, msg = self.auth.admin_reset_password(usuario)
                if sucesso:
                    self._registrar_log("ADMIN_RESET_SENHA", f"Resetou senha de: {usuario}")
                    messagebox.showinfo("Sucesso", msg, parent=top)
                    top.destroy()
                else:
                    messagebox.showerror("Erro", msg, parent=top)

        ttk.Button(top, text="RESETAR SENHA", style="Warning.TButton", command=confirmar_reset).pack(fill='x', padx=20, pady=15)

    # --- ADMINISTRAÇÃO: EXCLUSÃO ---
    def abrir_janela_exclusao(self):
        top = tk.Toplevel(self.root)
        top.title("Bloquear Usuário")
        top.geometry("300x350")
        top.configure(bg=COLOR_BG)
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 150
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 175
        top.geometry(f"+{x}+{y}")

        ttk.Label(top, text="Selecione para Bloquear", font=("Segoe UI", 10, "bold"), background=COLOR_BG).pack(pady=10)

        frame_list = ttk.Frame(top, style="Main.TFrame")
        frame_list.pack(fill='both', expand=True, padx=20, pady=5)
        lst_users = tk.Listbox(frame_list, height=10)
        lst_users.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(frame_list, orient="vertical", command=lst_users.yview)
        scrollbar.pack(side='right', fill='y')
        lst_users.config(yscrollcommand=scrollbar.set)

        users = self.auth.get_users_list()
        for u in users: lst_users.insert(tk.END, u)

        def confirmar_exclusao():
            sel = lst_users.curselection()
            if not sel: return
            usuario = lst_users.get(sel[0])
            if usuario == "admin": 
                if not messagebox.askyesno("Cuidado", "Apagar o 'admin' principal?", parent=top): return
            if messagebox.askyesno("Confirmar", f"Bloquear '{usuario}'?", parent=top):
                sucesso, msg = self.auth.delete_user(usuario)
                if sucesso:
                    self._registrar_log("ADMIN_BLOQUEAR", f"Bloqueou usuário: {usuario}")
                    messagebox.showinfo("Sucesso", msg, parent=top)
                    top.destroy()
                else: messagebox.showerror("Erro", msg, parent=top)

        ttk.Button(top, text="BLOQUEAR", style="Danger.TButton", command=confirmar_exclusao).pack(fill='x', padx=20, pady=15)

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
        self.add_linha_compacta(lf_val, "Intervalo de Crédito", self.vars[key]['passo'], 0, 1, "moeda")
        self.add_linha_compacta(lf_val, "Crédito Inicial", self.vars[key]['credito_ini'], 1, 0, "moeda")
        self.add_linha_compacta(lf_val, "Crédito Final", self.vars[key]['credito_fim'], 1, 1, "moeda")
        lf_val.columnconfigure(0, weight=1); lf_val.columnconfigure(1, weight=1)
        
        btn_frame = ttk.Frame(content, style="Main.TFrame")
        btn_frame.pack(fill='x', pady=10)
        ttk.Button(btn_frame, text="💾 SALVAR LOCALMENTE", style="Sec.TButton", command=lambda: self.gerar_padrao_local(key)).pack(side='left', fill='x', expand=True, padx=(0, 5), ipady=5)
        ttk.Button(btn_frame, text="☁️ ATUALIZAR TABELA AGORA", style="Action.TButton", command=lambda: self.gerar_padrao(key)).pack(side='right', fill='x', expand=True, padx=(5, 0), ipady=5)

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
        self.add_linha_compacta(lf_taxas, "Administração", self.vars[key]['adm'], 0, 0, "porcentagem", width=6)
        self.add_linha_compacta(lf_taxas, "Seguro de vida", self.vars[key]['seguro'], 1, 0, "porcentagem", width=6)
        lf_range = ttk.LabelFrame(content, text="VALORES", style="Card.TLabelframe", padding=5)
        lf_range.pack(fill='x', pady=(0, 8))
        self.add_linha_compacta(lf_range, "Prazo", self.vars[key]['prazo'], 0, 0, "numero")
        self.add_linha_compacta(lf_range, "Intervalo de Crédito", self.vars[key]['passo'], 0, 1, "moeda")
        self.add_linha_compacta(lf_range, "Crédito Inicial", self.vars[key]['credito_ini'], 1, 0, "moeda")
        self.add_linha_compacta(lf_range, "Crédito Final", self.vars[key]['credito_fim'], 1, 1, "moeda")
        lf_range.columnconfigure(0, weight=1); lf_range.columnconfigure(1, weight=1)
        bottom_frame = ttk.Frame(content, style="Main.TFrame")
        bottom_frame.pack(fill='x', pady=5)
        ttk.Checkbutton(bottom_frame, text="Tabela Apenas C/SV", variable=self.vars[key]['apenas_csv']).pack(side='left')
        btn_frame = ttk.Frame(content, style="Main.TFrame")
        btn_frame.pack(fill='x', pady=10)
        ttk.Button(btn_frame, text="💾 SALVAR LOCALMENTE", style="Sec.TButton", command=self.gerar_especial_local).pack(side='left', fill='x', expand=True, padx=(0, 5), ipady=5)
        ttk.Button(btn_frame, text="CRIAR NOVA TABELA AGORA", style="Action.TButton", command=self.gerar_especial).pack(side='right', fill='x', expand=True, padx=(5, 0), ipady=5)

    # --- ABA EDITOR JSON ---
    def setup_tab_editor(self):
        content = ttk.Frame(self.tab_editor, style="Main.TFrame", padding=10)
        content.pack(fill='both', expand=True)
        
        # --- Barra Superior ---
        top_bar = ttk.Frame(content, style="Main.TFrame")
        top_bar.pack(fill='x', pady=(0, 10))
        ttk.Button(top_bar, text="⬇️ Carregar Tabelas Atuais", style="Sec.TButton", command=self.editor_carregar_nuvem).pack(side='left', padx=(0, 5))
        self.lbl_editor_status = ttk.Label(top_bar, text="...", foreground=COLOR_TEXT_SUB)
        self.lbl_editor_status.pack(side='left', padx=5)
        ttk.Button(top_bar, text="💾 Salvar Local", style="Sec.TButton", command=self.editor_salvar_local).pack(side='right', padx=(5, 0))
        ttk.Button(top_bar, text="☁️ ENVIAR", style="Action.TButton", command=self.editor_salvar_nuvem).pack(side='right', padx=(5, 0))
        ttk.Button(top_bar, text="↩ Desfazer", style="Warning.TButton", command=self.editor_reverter).pack(side='right')
        
        # --- Painel Dividido ---
        paned = tk.PanedWindow(content, orient=tk.HORIZONTAL, bg=COLOR_BG, sashwidth=4, showhandle=True)
        paned.pack(fill='both', expand=True)
        
        # === COLUNA DA ESQUERDA (LISTA + BOTÕES) ===
        frame_list = ttk.Frame(paned, style="Main.TFrame")
        paned.add(frame_list, width=200)
        
        # 1. Título
        ttk.Label(frame_list, text="TABELAS (dados_consorcio)", font=("Segoe UI", 8, "bold"), foreground=COLOR_TEXT_SUB).pack(side='top', anchor='w', pady=(0, 5))
        
        # 2. Container para Lista e Scrollbar
        list_container = ttk.Frame(frame_list)
        list_container.pack(side='top', fill='both', expand=True)

        scroll_lst = ttk.Scrollbar(list_container)
        scroll_lst.pack(side='right', fill='y')
        
        self.lst_tabelas = tk.Listbox(list_container, font=("Segoe UI", 9), borderwidth=1, relief="solid", yscrollcommand=scroll_lst.set)
        self.lst_tabelas.pack(side='left', fill='both', expand=True)
        scroll_lst.config(command=self.lst_tabelas.yview)
        self.lst_tabelas.bind('<<ListboxSelect>>', self.editor_selecionar_tabela)

        # 3. Botões de Mover
        btn_move_frame = ttk.Frame(frame_list, style="Main.TFrame")
        btn_move_frame.pack(side='top', fill='x', pady=5) 
        
        ttk.Button(btn_move_frame, text="▲ Cima", style="Sec.TButton", command=self.editor_mover_cima).pack(side='left', fill='x', expand=True, padx=(0, 2))
        ttk.Button(btn_move_frame, text="▼ Baixo", style="Sec.TButton", command=self.editor_mover_baixo).pack(side='left', fill='x', expand=True, padx=(2, 0))

        # === COLUNA DA DIREITA (EDIÇÃO) ===
        self.frame_edit = ttk.Frame(paned, style="Main.TFrame", padding=(10, 0, 0, 0))
        paned.add(self.frame_edit)
        
        # Metadados
        lf_meta = ttk.LabelFrame(self.frame_edit, text="DADOS BÁSICOS", style="Card.TLabelframe", padding=10)
        lf_meta.pack(fill='x', pady=(0, 10))
        self.add_linha_compacta(lf_meta, "ID da tabela", self.vars['editor']['id'], 0, 0, "texto", width=20)
        self.add_linha_compacta(lf_meta, "Nome da tabela", self.vars['editor']['name'], 0, 1, "texto", width=20)
        self.add_linha_compacta(lf_meta, "Categoria", self.vars['editor']['category'], 1, 0, "texto")
        self.add_linha_compacta(lf_meta, "Plano", self.vars['editor']['plan'], 1, 1, "texto")
        self.add_linha_compacta(lf_meta, "Taxa de administração", self.vars['editor']['adm'], 2, 0, "texto")
        self.add_linha_compacta(lf_meta, "Seguro de vida", self.vars['editor']['seguro'], 2, 1, "texto")
        lf_meta.columnconfigure(0, weight=1); lf_meta.columnconfigure(1, weight=1)
        
        btn_meta = ttk.Frame(lf_meta, style="Main.TFrame")
        btn_meta.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky='ew')
        ttk.Button(btn_meta, text="Salvar Dados", style="Sec.TButton", command=self.editor_atualizar_metadados).pack(side='left', fill='x', expand=True, padx=(0, 5))
        ttk.Button(btn_meta, text="Converter p/ Seguro Obrigatório", style="Warning.TButton", command=self.editor_converter_seguro).pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(btn_meta, text="Excluir Tabela", style="Danger.TButton", command=self.editor_excluir_tabela).pack(side='right', fill='x', expand=True, padx=(5, 0))
        
        # Treeview (Dados)
        lf_data = ttk.LabelFrame(self.frame_edit, text="CRÉDITOS (Expanda para ver prazos)", style="Card.TLabelframe", padding=10)
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
    def editor_carregar_nuvem(self):
        self.lbl_editor_status.config(text="Baixando...", foreground=COLOR_WARNING); self.root.update()
        try:
            data = carregar_dados_tabelas() 
            self.editor_data = data; self.editor_backup = copy.deepcopy(data)
            self.lbl_editor_status.config(text=FILE_DADOS, foreground=COLOR_SUCCESS)
            self.editor_refresh_lista(); self.tree_data.delete(*self.tree_data.get_children()); self.selected_table_id = None
        except Exception as e:
            self.lbl_editor_status.config(text="Erro", foreground=COLOR_DANGER); messagebox.showerror("Erro Download", f"{e}")

    def editor_salvar_nuvem(self):
        self.lbl_editor_status.config(text="Enviando...", foreground=COLOR_WARNING); self.root.update()
        try:
            upload_json_supabase(FILE_DADOS, self.editor_data) 
            self.editor_backup = copy.deepcopy(self.editor_data); self.lbl_editor_status.config(text="Salvo!", foreground=COLOR_SUCCESS)
            self._registrar_log("EDITOR_SALVAR_NUVEM", "Atualizou o arquivo mestre de tabelas no Supabase")
            messagebox.showinfo("Sucesso", "Dados atualizados no servidor!")
        except Exception as e:
            self.lbl_editor_status.config(text="Erro", foreground=COLOR_DANGER); messagebox.showerror("Erro Upload", f"{e}")

    def editor_salvar_local(self):
        path = filedialog.asksaveasfilename(title="Salvar JSON Local", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="dados_consorcio_backup.json")
        if not path: return
        try:
            with open(path, 'w', encoding='utf-8') as f: json.dump(self.editor_data, f, indent=4, ensure_ascii=False)
            self._registrar_log("EDITOR_SALVAR_LOCAL", f"Salvo em: {path}")
            messagebox.showinfo("Salvo", f"Arquivo salvo localmente em:\n{path}")
        except Exception as e: messagebox.showerror("Erro", str(e))

    def editor_refresh_lista(self):
        self.lst_tabelas.delete(0, tk.END)
        if not self.editor_data: return
        if "metadata" in self.editor_data:
            for item in self.editor_data["metadata"]: self.lst_tabelas.insert(tk.END, item.get("id", "?"))

    # --- FUNÇÕES: MOVER ITENS NA LISTA ---
    def editor_mover_cima(self):
        sel = self.lst_tabelas.curselection()
        if not sel: return
        idx = sel[0]
        if idx == 0: return # Já está no topo

        meta = self.editor_data["metadata"]
        meta[idx], meta[idx-1] = meta[idx-1], meta[idx]
        
        self.editor_refresh_lista()
        self.lst_tabelas.selection_set(idx-1)
        self.lst_tabelas.see(idx-1)

    def editor_mover_baixo(self):
        sel = self.lst_tabelas.curselection()
        if not sel: return
        idx = sel[0]
        meta = self.editor_data["metadata"]
        if idx >= len(meta) - 1: return # Já está em baixo

        meta[idx], meta[idx+1] = meta[idx+1], meta[idx]

        self.editor_refresh_lista()
        self.lst_tabelas.selection_set(idx+1)
        self.lst_tabelas.see(idx+1)
    # --------------------------------------------

    def editor_selecionar_tabela(self, event):
        sel = self.lst_tabelas.curselection()
        if not sel: return
        t_id = self.lst_tabelas.get(sel[0]); self.selected_table_id = t_id
        meta = next((m for m in self.editor_data["metadata"] if m["id"] == t_id), None)
        if meta:
            self.vars['editor']['id'].set(meta.get('id', '')); self.vars['editor']['name'].set(meta.get('name', ''))
            self.vars['editor']['category'].set(meta.get('category', '')); self.vars['editor']['plan'].set(meta.get('plan', ''))
            self.vars['editor']['adm'].set(meta.get('taxaAdmin', 0.0)); self.vars['editor']['fundo'].set(meta.get('fundoReserva', 0.0))
            self.vars['editor']['seguro'].set(meta.get('seguroPct', 0.0))
        self.tree_data.delete(*self.tree_data.get_children())
        rows = self.editor_data["data"].get(t_id, [])
        rows.sort(key=lambda x: x.get('credito', 0))
        for i, r in enumerate(rows):
            credito = r.get('credito', 0); cred_fmt = f"R$ {credito:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            parent_id = self.tree_data.insert("", "end", iid=f"c_{i}", text=cred_fmt, values=("Expandir",), open=False)
            prazos = r.get('prazos', []); 
            prazos.sort(key=lambda x: x.get('prazo', 0), reverse=True) 
            
            for j, p in enumerate(prazos):
                prazo_meses = p.get('prazo', 0); val_unico = p.get('parcela', None); val_csv = p.get('parcela_CSV', 0); val_ssv = p.get('parcela_SSV', None)
                if val_unico is not None: detalhe = f"Parcela: R$ {val_unico:.2f}"
                else:
                    detalhe = f"CSV: {val_csv:.2f}"
                    if val_ssv is not None: detalhe += f" | SSV: {val_ssv:.2f}"
                self.tree_data.insert(parent_id, "end", iid=f"p_{i}_{j}", text=f"{prazo_meses}m", values=(detalhe,))

    def editor_atualizar_metadados(self):
        old_id = self.selected_table_id
        if not old_id: return
        
        # Captura novos valores
        new_id = self.vars['editor']['id'].get().strip()
        new_name = self.vars['editor']['name'].get().strip()
        
        if not new_id or not new_name:
            messagebox.showwarning("Aviso", "ID e Nome da tabela são obrigatórios.")
            return

        if new_id != old_id:
            existe = any(m["id"] == new_id for m in self.editor_data["metadata"] if m["id"] != old_id)
            if existe:
                messagebox.showerror("Erro", f"O ID '{new_id}' já está sendo usado em outra tabela.")
                return

        found = False
        for m in self.editor_data["metadata"]:
            if m["id"] == old_id:
                m["id"] = new_id 
                m["name"] = new_name 
                m["category"] = self.vars['editor']['category'].get()
                m["plan"] = self.vars['editor']['plan'].get()
                m["taxaAdmin"] = self.vars['editor']['adm'].get()
                m["seguroPct"] = self.vars['editor']['seguro'].get()
                found = True
                break
        
        if not found: return

        if new_id != old_id:
            if old_id in self.editor_data["data"]:
                self.editor_data["data"][new_id] = self.editor_data["data"].pop(old_id)
            
            self.selected_table_id = new_id
            self.editor_refresh_lista()
            
            items = self.lst_tabelas.get(0, tk.END)
            try:
                idx = items.index(new_id)
                self.lst_tabelas.selection_clear(0, tk.END)
                self.lst_tabelas.selection_set(idx)
                self.lst_tabelas.see(idx)
            except: pass

        self._registrar_log("EDITOR_METADATA", f"Atualizou metadados da tabela {old_id} -> {new_id}")
        messagebox.showinfo("OK", "Dados Salvos (ID/Nome/Taxas atualizados).\nClique em ENVIAR para atualizar ONLINE.")

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
            self._registrar_log("EDITOR_CONVERT", f"Converteu {alteracoes} itens para Seguro Obrigatório na tabela {t_id}")
            messagebox.showinfo("OK", f"{alteracoes} convertidos.")
        else: messagebox.showinfo("Aviso", "Nada alterado.")

    def editor_excluir_tabela(self):
        t_id = self.selected_table_id
        if not t_id: return
        if not messagebox.askyesno("Confirmar", f"Excluir tabela '{t_id}'?"): return
        self.editor_data["metadata"] = [m for m in self.editor_data["metadata"] if m["id"] != t_id]
        if t_id in self.editor_data["data"]: del self.editor_data["data"][t_id]
        self._registrar_log("EDITOR_DELETE_TABLE", f"Excluiu tabela {t_id}")
        self.editor_refresh_lista(); self.tree_data.delete(*self.tree_data.get_children()); self.selected_table_id = None

    def editor_excluir_item(self):
        sel = self.tree_data.selection(); 
        if not sel: return
        item_id = sel[0]; t_id = self.selected_table_id
        if t_id not in self.editor_data["data"]: return
        rows = self.editor_data["data"][t_id]
        if item_id.startswith("c_"):
            idx_cred = int(item_id.split("_")[1])
            if not messagebox.askyesno("Excluir", "Deseja excluir TODO o crédito?"): return
            del rows[idx_cred]; self.editor_data["data"][t_id] = rows; self.editor_selecionar_tabela(None)
            self._registrar_log("EDITOR_DELETE_CREDIT", f"Excluiu crédito index {idx_cred} da tabela {t_id}")
        elif item_id.startswith("p_"):
            parts = item_id.split("_"); idx_cred = int(parts[1]); idx_prazo = int(parts[2])
            cred_row = rows[idx_cred]; prazos = cred_row.get('prazos', [])
            if len(prazos) <= 1:
                if messagebox.askyesno("Aviso Crítico", "Único prazo. Excluir crédito inteiro?"): 
                    del rows[idx_cred]
                    self._registrar_log("EDITOR_DELETE_CREDIT", f"Excluiu crédito index {idx_cred} (último prazo) da tabela {t_id}")
                else: return
            else:
                if not messagebox.askyesno("Confirmar", "Excluir apenas esta opção?"): return
                del rows[idx_cred]['prazos'][idx_prazo]
                self._registrar_log("EDITOR_DELETE_PRAZO", f"Excluiu prazo index {idx_prazo} do crédito {idx_cred} tabela {t_id}")
            self.editor_data["data"][t_id] = rows; self.editor_selecionar_tabela(None)

    def editor_reverter(self):
        if not self.editor_backup: return
        if messagebox.askyesno("Reverter", "Desfazer alterações locais?"): 
            self.editor_data = copy.deepcopy(self.editor_backup); self.editor_refresh_lista(); self.tree_data.delete(*self.tree_data.get_children()); self.selected_table_id = None

    # --- ABA PDF (CLOUD & LOCAL) ---
    def setup_tab_pdf(self):
        content = ttk.Frame(self.tab_pdf, style="Main.TFrame", padding=15)
        content.pack(fill='both', expand=True)

        # --- Seleção de Arquivo ---
        lf_sel = ttk.LabelFrame(content, text="ARQUIVO DO RESULTADO DE ASSEMBLEIAS (PDF)", style="Card.TLabelframe", padding=10)
        lf_sel.pack(fill='x', pady=(0, 10))
        
        row_file = ttk.Frame(lf_sel, style="Main.TFrame")
        row_file.pack(fill='x')
        
        ttk.Button(row_file, text="📁 Selecionar PDF...", style="Sec.TButton", command=self.selecionar_pdf).pack(side='left', padx=(0, 10))
        lbl_path = ttk.Label(row_file, textvariable=self.vars['pdf']['path'], foreground=COLOR_TEXT_SUB, width=40)
        lbl_path.pack(side='left', fill='x', expand=True)
        
        # --- BOTÕES LADO A LADO ---
        btn_frame = ttk.Frame(content, style="Main.TFrame")
        btn_frame.pack(fill='x', pady=10) 

        # Botão 1: Salvar Local
        ttk.Button(btn_frame, text="💾 EXTRAIR E SALVAR LOCALMENTE", style="Sec.TButton", command=self.executar_processamento_pdf_local).pack(side='left', fill='x', expand=True, padx=(0, 5), ipady=5)
        
        # Botão 2: Atualizar Nuvem
        ttk.Button(btn_frame, text="☁️ EXTRAIR E ATUALIZAR SERVIDOR", style="Action.TButton", command=self.executar_processamento_pdf).pack(side='left', fill='x', expand=True, padx=(5, 0), ipady=5)
        
        # --- Log ---
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
        
        if not dados: 
            self.log_pdf("❌ Falha na extração ou PDF vazio.")
            return

        self.log_pdf(f"✅ {len(dados)} registros extraídos. Iniciando sincronização...")

        try:
            # 1. Atualiza estatisticas_grupo.json (Estado Atual)
            self.log_pdf("Atualizando status atual dos grupos...")
            novos, atualizados = atualizar_estatisticas_json(dados)
            self.log_pdf(f"STATUS ATUAL: +{novos} Novos | ⟳{atualizados} Atualizados")
            
            # 2. Atualiza historico_assembleias.json (Histórico Temporal)
            self.log_pdf("Atualizando histórico de assembleias...")
            add_hist, up_hist = atualizar_historico_assembleias(dados)
            self.log_pdf(f"HISTÓRICO: +{add_hist} Registros de Tempo | ⟳{up_hist} Corrigidos")
            
            self._registrar_log("PDF_PROCESS_CLOUD", f"Processou PDF {os.path.basename(pdf_path)} na nuvem")

            messagebox.showinfo("Concluído", 
                                f"Sincronização Finalizada!\n\n"
                                f"Status Atual: {novos} novos / {atualizados} atz\n"
                                f"Histórico: {add_hist} novos / {up_hist} atz")

        except Exception as e:
            self.log_pdf(f"❌ Erro de Sincronização: {str(e)}")
            print(e)

    def _thread_pdf_local(self, pdf_path):
        self.log_pdf("Extraindo dados do PDF (Modo Local)...")
        dados = extrair_dados_pdf(pdf_path, callback_log=self.log_pdf)
        if not dados: self.log_pdf("❌ Falha na extração."); return
        path_save = filedialog.asksaveasfilename(title="Salvar Extração Local", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="estatisticas_extraidas.json")
        if not path_save: self.log_pdf("Operação cancelada."); return
        try:
            with open(path_save, 'w', encoding='utf-8') as f: json.dump(dados, f, indent=4, ensure_ascii=False)
            self._registrar_log("PDF_PROCESS_LOCAL", f"Salvou extração em {path_save}")
            self.log_pdf(f"💾 Salvo em: {path_save}"); messagebox.showinfo("Sucesso", "Dados extraídos e salvos localmente!")
        except Exception as e: self.log_pdf(f"❌ Erro ao salvar: {e}")

    # --- ABA RELAÇÃO (CLOUD & LOCAL) ---
    def setup_tab_relacao(self):
        content = ttk.Frame(self.tab_relacao, style="Main.TFrame", padding=10)
        content.pack(fill='both', expand=True)
        
        # Barra Superior (Upload/Download)
        top_bar = ttk.Frame(content, style="Main.TFrame")
        top_bar.pack(fill='x', pady=(0, 10))
        ttk.Button(top_bar, text="⬇️ Carregar Relação de Grupos", style="Sec.TButton", command=self.relacao_carregar_nuvem).pack(side='left', padx=(0, 5))
        self.lbl_relacao_status = ttk.Label(top_bar, text="...", foreground=COLOR_TEXT_SUB)
        self.lbl_relacao_status.pack(side='left', padx=5)
        ttk.Button(top_bar, text="💾 Salvar Local", style="Sec.TButton", command=self.relacao_salvar_local).pack(side='right', padx=(5, 0))
        ttk.Button(top_bar, text="☁️ ENVIAR", style="Action.TButton", command=self.relacao_salvar_nuvem).pack(side='right', padx=(5, 0))
        ttk.Button(top_bar, text="↩ Desfazer", style="Warning.TButton", command=self.relacao_reverter).pack(side='right')
        
        # Painel Dividido (Lista | Detalhes)
        paned = tk.PanedWindow(content, orient=tk.HORIZONTAL, bg=COLOR_BG, sashwidth=4, showhandle=True)
        paned.pack(fill='both', expand=True)
        
        # Coluna Esquerda: Lista de Grupos
        frame_list = ttk.Frame(paned, style="Main.TFrame")
        paned.add(frame_list, width=220)
        
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
        
        # Coluna Direita: Campos Dinâmicos
        right_panel = ttk.Frame(paned, style="Main.TFrame", padding=(10, 0, 0, 0))
        paned.add(right_panel)
        
        toolbar_fields = ttk.LabelFrame(right_panel, text="Adicione ou Remova Campos de Informações", style="Card.TLabelframe", padding=5)
        toolbar_fields.pack(fill='x', pady=(0, 5))
        
        ttk.Button(toolbar_fields, text="➕ Add Global", style="Sec.TButton", command=self.relacao_add_global_field).pack(side='left', padx=(0, 5))
        ttk.Button(toolbar_fields, text="➕ Add Local", style="Sec.TButton", command=self.relacao_add_local_field).pack(side='left', padx=(0, 5)) 
        
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

    # --- Lógica Relação ---
    def relacao_carregar_nuvem(self):
        self.lbl_relacao_status.config(text="Baixando...", foreground=COLOR_WARNING); self.root.update()
        try:
            raw_list = download_json_supabase(FILE_RELACAO); self.relacao_data = {}
            for item in raw_list: gid = str(item.get("Grupo", "S/N")); self.relacao_data[gid] = item
            self.relacao_backup = copy.deepcopy(self.relacao_data); self.lbl_relacao_status.config(text=FILE_RELACAO, foreground=COLOR_SUCCESS)
            self.relacao_refresh_list(); self.relacao_limpar_painel()
        except Exception as e: self.lbl_relacao_status.config(text="Erro", foreground=COLOR_DANGER); messagebox.showerror("Erro Download", f"{e}")

    def relacao_salvar_nuvem(self):
        self.relacao_atualizar_memoria(); erros = []
        for grp, dados in self.relacao_data.items():
            for k, v in dados.items():
                if v is None or str(v).strip() == "": erros.append(f"Grupo {grp} -> Campo '{k}' vazio.")
        if erros: messagebox.showerror("Erro Validação", "\n".join(erros[:5])); return
        self.lbl_relacao_status.config(text="Enviando...", foreground=COLOR_WARNING); self.root.update()
        try:
            final_list = list(self.relacao_data.values())
            try: final_list.sort(key=lambda x: int(x.get("Grupo", 0)))
            except: pass
            upload_json_supabase(FILE_RELACAO, final_list)
            self._registrar_log("RELACAO_SALVAR_NUVEM", "Atualizou a relação de grupos no servidor")
            self.relacao_backup = copy.deepcopy(self.relacao_data); self.lbl_relacao_status.config(text="Salvo!", foreground=COLOR_SUCCESS)
            messagebox.showinfo("Sucesso", "Relação salva no servidor!")
        except Exception as e: self.lbl_relacao_status.config(text="Erro", foreground=COLOR_DANGER); messagebox.showerror("Erro Upload", f"{e}")

    def relacao_salvar_local(self):
        self.relacao_atualizar_memoria()
        path = filedialog.asksaveasfilename(title="Salvar Relação Local", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="relacao_grupos_backup.json")
        if not path: return
        try:
            final_list = list(self.relacao_data.values())
            try: final_list.sort(key=lambda x: int(x.get("Grupo", 0)))
            except: pass
            with open(path, 'w', encoding='utf-8') as f: json.dump(final_list, f, indent=4, ensure_ascii=False)
            self._registrar_log("RELACAO_SALVAR_LOCAL", f"Salvo em: {path}")
            messagebox.showinfo("Salvo", f"Arquivo salvo localmente em:\n{path}")
        except Exception as e: messagebox.showerror("Erro", str(e))

    def relacao_refresh_list(self):
        self.lst_grupos.delete(0, tk.END)
        try: sorted_keys = sorted(self.relacao_data.keys(), key=lambda x: int(x))
        except: sorted_keys = sorted(self.relacao_data.keys())
        for k in sorted_keys: self.lst_grupos.insert(tk.END, k)

    def relacao_limpar_painel(self):
        for widget in self.frame_dynamic_fields.winfo_children(): widget.destroy()
        self.relacao_vars_cache = {}; self.relacao_selected_grupo = None

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
            f = ttk.Frame(self.frame_dynamic_fields, style="Main.TFrame"); f.pack(fill='x', pady=2)
            ttk.Label(f, text=key, width=20).pack(side='left')
            var = tk.StringVar(value=str(val)); self.relacao_vars_cache[key] = var
            entry = ttk.Entry(f, textvariable=var)
            if key == "Grupo": entry.config(state='readonly') 
            entry.pack(side='left', fill='x', expand=True)

    def relacao_selecionar_grupo(self, event):
        sel = self.lst_grupos.curselection()
        if not sel: return
        self.relacao_atualizar_memoria(); grp_id = self.lst_grupos.get(sel[0])
        self.relacao_selected_grupo = grp_id; self._renderizar_campos_grupo(grp_id)

    def relacao_novo_grupo(self):
        if not self.relacao_data: messagebox.showwarning("Aviso", "Carregue do servidor primeiro."); return
        new_id = simpledialog.askstring("Novo Grupo", "Número:")
        if not new_id: return
        if new_id in self.relacao_data: messagebox.showerror("Erro", "Já existe."); return
        first_key = list(self.relacao_data.keys())[0]; template = self.relacao_data[first_key]
        new_obj = {}
        for k in template.keys():
            if k == "Grupo":
                try: new_obj[k] = int(new_id)
                except: new_obj[k] = new_id
            else: new_obj[k] = ""
        self.relacao_data[new_id] = new_obj; self.relacao_refresh_list()
        self._registrar_log("RELACAO_ADD_GRUPO", f"Adicionou grupo {new_id}")

    def relacao_excluir_grupo(self):
        sel = self.lst_grupos.curselection()
        if not sel: return
        grp_id = self.lst_grupos.get(sel[0])
        if messagebox.askyesno("Excluir", f"Apagar {grp_id}?"):
            if grp_id == self.relacao_selected_grupo: self.relacao_limpar_painel()
            del self.relacao_data[grp_id]; self.relacao_refresh_list()
            self._registrar_log("RELACAO_DEL_GRUPO", f"Removeu grupo {grp_id}")

    def relacao_add_global_field(self):
        if not self.relacao_data: return
        field_name = simpledialog.askstring("Novo Campo", "Digite o nome do campo:")
        if not field_name: return
        for grp in self.relacao_data:
            if field_name not in self.relacao_data[grp]: self.relacao_data[grp][field_name] = ""
        if self.relacao_selected_grupo: self.lst_grupos.event_generate("<<ListboxSelect>>")
        self._registrar_log("RELACAO_ADD_FIELD_GLOBAL", f"Adicionou campo global: {field_name}")

    def relacao_add_local_field(self):
        """Adiciona um campo APENAS no grupo selecionado atualmente"""
        if not self.relacao_selected_grupo: 
            messagebox.showwarning("Aviso", "Selecione um grupo primeiro.")
            return
        
        # Salva o que já foi digitado nos outros campos antes de atualizar a tela
        self.relacao_atualizar_memoria()

        field_name = simpledialog.askstring("Novo Campo Local", "Digite o nome do campo:")
        if not field_name: return
        
        # Verifica se já existe neste grupo
        if field_name in self.relacao_data[self.relacao_selected_grupo]:
            messagebox.showwarning("Erro", "Este campo já existe neste grupo.")
            return

        # Adiciona o campo vazio apenas neste grupo
        self.relacao_data[self.relacao_selected_grupo][field_name] = ""
        self._registrar_log("RELACAO_ADD_FIELD_LOCAL", f"Adicionou campo {field_name} ao grupo {self.relacao_selected_grupo}")
        
        # Atualiza a visualização
        self._renderizar_campos_grupo(self.relacao_selected_grupo)

    def relacao_del_global_field(self):
        if not self.relacao_data: return
        self.relacao_atualizar_memoria()
        field_name = simpledialog.askstring("Excluir Global", "Digite o nome do campo:")
        if not field_name: return
        if field_name == "Grupo": return
        count = 0
        for grp in self.relacao_data:
            if field_name in self.relacao_data[grp]: del self.relacao_data[grp][field_name]; count += 1
        if count > 0:
            if self.relacao_selected_grupo: self._renderizar_campos_grupo(self.relacao_selected_grupo)
            self._registrar_log("RELACAO_DEL_FIELD_GLOBAL", f"Removeu campo {field_name} de {count} grupos")
            messagebox.showinfo("Info", f"Removido de {count}.")

    def relacao_del_local_field(self):
        if not self.relacao_selected_grupo: return
        self.relacao_atualizar_memoria()
        field_name = simpledialog.askstring("Excluir Local", "Digite o nome do campo:")
        if not field_name: return
        if field_name == "Grupo": return
        dados = self.relacao_data[self.relacao_selected_grupo]
        if field_name in dados: 
            del self.relacao_data[self.relacao_selected_grupo][field_name]
            self._renderizar_campos_grupo(self.relacao_selected_grupo)
            self._registrar_log("RELACAO_DEL_FIELD_LOCAL", f"Removeu campo {field_name} do grupo {self.relacao_selected_grupo}")

    def relacao_reverter(self):
        if not self.relacao_backup: return
        if messagebox.askyesno("Desfazer", "Reverter para o estado do servidor?"):
            self.relacao_data = copy.deepcopy(self.relacao_backup); self.relacao_refresh_list(); self.relacao_limpar_painel()

    # --- ABA MENSAGENS / TICKER (NOVA) ---
    def setup_tab_mensagens(self):
        content = ttk.Frame(self.tab_mensagens, style="Main.TFrame", padding=15)
        content.pack(fill='both', expand=True)

        # Barra Superior
        top_bar = ttk.Frame(content, style="Main.TFrame")
        top_bar.pack(fill='x', pady=(0, 10))
        
        ttk.Button(top_bar, text="⬇️ Carregar Mensagens", style="Sec.TButton", command=self.mensagens_carregar_nuvem).pack(side='left', padx=(0, 5))
        self.lbl_msg_status = ttk.Label(top_bar, text="...", foreground=COLOR_TEXT_SUB)
        self.lbl_msg_status.pack(side='left', padx=5)

        ttk.Button(top_bar, text="💾 Salvar Local", style="Sec.TButton", command=self.mensagens_salvar_local).pack(side='right', padx=(5, 0))
        ttk.Button(top_bar, text="☁️ ENVIAR", style="Action.TButton", command=self.mensagens_salvar_nuvem).pack(side='right', padx=(5, 0))
        
        # Painel Principal (Lista)
        lf_list = ttk.LabelFrame(content, text="MENSAGENS ATIVAS", style="Card.TLabelframe", padding=10)
        lf_list.pack(fill='both', expand=True, pady=(0, 10))

        scroll_msg = ttk.Scrollbar(lf_list)
        scroll_msg.pack(side='right', fill='y')

        self.lst_mensagens = tk.Listbox(lf_list, font=("Segoe UI", 10), height=15, borderwidth=1, relief="solid", yscrollcommand=scroll_msg.set)
        self.lst_mensagens.pack(side='left', fill='both', expand=True)
        scroll_msg.config(command=self.lst_mensagens.yview)
        self.lst_mensagens.bind('<<ListboxSelect>>', self.mensagens_selecionar)

        # Painel Inferior (Edição)
        bottom_panel = ttk.Frame(content, style="Main.TFrame")
        bottom_panel.pack(fill='x')
        
        # Entrada de Texto
        ttk.Label(bottom_panel, text="Texto da Mensagem:").pack(anchor='w', pady=(0, 2))
        self.entry_msg = ttk.Entry(bottom_panel, textvariable=self.vars['msg']['input'])
        self.entry_msg.pack(fill='x', pady=(0, 8))
        
        # Botões de Ação
        btn_row = ttk.Frame(bottom_panel, style="Main.TFrame")
        btn_row.pack(fill='x')

        ttk.Button(btn_row, text="➕ Adicionar Nova", style="Sec.TButton", command=self.mensagens_adicionar).pack(side='left', fill='x', expand=True, padx=(0, 5))
        ttk.Button(btn_row, text="✏️ Atualizar Selecionada", style="Warning.TButton", command=self.mensagens_editar).pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(btn_row, text="🗑️ Excluir", style="Danger.TButton", command=self.mensagens_excluir).pack(side='left', fill='x', expand=True, padx=(5, 0))

        # Botões de Ordem
        order_row = ttk.Frame(bottom_panel, style="Main.TFrame")
        order_row.pack(fill='x', pady=(8, 0))
        ttk.Button(order_row, text="▲ Mover para Cima", style="Sec.TButton", command=self.mensagens_mover_cima).pack(side='left', fill='x', expand=True, padx=(0, 2))
        ttk.Button(order_row, text="▼ Mover para Baixo", style="Sec.TButton", command=self.mensagens_mover_baixo).pack(side='left', fill='x', expand=True, padx=(2, 0))

    # --- Lógica Mensagens ---
    def mensagens_carregar_nuvem(self):
        self.lbl_msg_status.config(text="Baixando...", foreground=COLOR_WARNING); self.root.update()
        try:
            data = download_json_supabase(FILE_MESSAGES)
            if data and isinstance(data, dict):
                self.messages_data = data
            elif data and isinstance(data, list):
                self.messages_data = {"messages": data, "lastUpdate": ""}
            else:
                self.messages_data = {"messages": [], "lastUpdate": ""}
            
            self.mensagens_refresh_list()
            self.lbl_msg_status.config(text=FILE_MESSAGES, foreground=COLOR_SUCCESS)
        except Exception as e:
            self.lbl_msg_status.config(text="Erro", foreground=COLOR_DANGER)
            messagebox.showerror("Erro Download", f"{e}")

    def mensagens_salvar_nuvem(self):
        self.lbl_msg_status.config(text="Enviando...", foreground=COLOR_WARNING); self.root.update()
        try:
            self.messages_data["lastUpdate"] = datetime.now().isoformat()
            upload_json_supabase(FILE_MESSAGES, self.messages_data)
            self._registrar_log("MESSAGES_SALVAR_NUVEM", "Atualizou mensagens rolantes no servidor")
            self.lbl_msg_status.config(text="Salvo!", foreground=COLOR_SUCCESS)
            messagebox.showinfo("Sucesso", "Mensagens atualizadas no servidor!")
        except Exception as e:
            self.lbl_msg_status.config(text="Erro", foreground=COLOR_DANGER)
            messagebox.showerror("Erro Upload", f"{e}")

    def mensagens_salvar_local(self):
        path = filedialog.asksaveasfilename(title="Salvar Mensagens Local", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="mensagens_backup.json")
        if not path: return
        try:
            self.messages_data["lastUpdate"] = datetime.now().isoformat()
            with open(path, 'w', encoding='utf-8') as f: json.dump(self.messages_data, f, indent=4, ensure_ascii=False)
            self._registrar_log("MESSAGES_SALVAR_LOCAL", f"Salvo em: {path}")
            messagebox.showinfo("Salvo", f"Arquivo salvo localmente em:\n{path}")
        except Exception as e: messagebox.showerror("Erro", str(e))

    def mensagens_refresh_list(self):
        self.lst_mensagens.delete(0, tk.END)
        msgs = self.messages_data.get("messages", [])
        for m in msgs:
            self.lst_mensagens.insert(tk.END, m)
        self.entry_msg.delete(0, tk.END)
        self.msg_selected_index = None

    def mensagens_selecionar(self, event):
        sel = self.lst_mensagens.curselection()
        if not sel: return
        idx = sel[0]
        self.msg_selected_index = idx
        msg = self.lst_mensagens.get(idx)
        self.vars['msg']['input'].set(msg)

    def mensagens_adicionar(self):
        txt = self.vars['msg']['input'].get().strip()
        if not txt: return
        self.messages_data["messages"].append(txt)
        self.mensagens_refresh_list()
        self.vars['msg']['input'].set("") # Limpa input

    def mensagens_editar(self):
        if self.msg_selected_index is None: return
        txt = self.vars['msg']['input'].get().strip()
        if not txt: return
        self.messages_data["messages"][self.msg_selected_index] = txt
        self.mensagens_refresh_list()

    def mensagens_excluir(self):
        if self.msg_selected_index is None: return
        if not messagebox.askyesno("Excluir", "Remover esta mensagem?"): return
        del self.messages_data["messages"][self.msg_selected_index]
        self.mensagens_refresh_list()

    def mensagens_mover_cima(self):
        if self.msg_selected_index is None or self.msg_selected_index == 0: return
        idx = self.msg_selected_index
        msgs = self.messages_data["messages"]
        msgs[idx], msgs[idx-1] = msgs[idx-1], msgs[idx]
        self.mensagens_refresh_list()
        self.lst_mensagens.selection_set(idx-1)
        self.mensagens_selecionar(None)

    def mensagens_mover_baixo(self):
        if self.msg_selected_index is None: return
        idx = self.msg_selected_index
        msgs = self.messages_data["messages"]
        if idx >= len(msgs) - 1: return
        msgs[idx], msgs[idx+1] = msgs[idx+1], msgs[idx]
        self.mensagens_refresh_list()
        self.lst_mensagens.selection_set(idx+1)
        self.mensagens_selecionar(None)

    # --- GERADOR (CLOUD & LOCAL) ---
    def salvar_estado_atual(self):
        dados = {k: {sk: sv.get() for sk, sv in v.items()} for k, v in self.vars.items() if k not in ['pdf','editor', 'msg']}
        salvar_config(dados)
    
    def gerar_padrao(self, grupo):
        self.salvar_estado_atual(); d = self.vars[grupo]; pl = d['plano'].get()
        chave = f"t_{('imovel' if grupo=='2011' else 'auto')}{grupo}_{('normal' if pl=='N' else pl)}"
        try:
            res = calcular_simulacao(grupo, pl, d['prazo'].get(), d['credito_ini'].get(), d['credito_fim'].get(), d['passo'].get())
            salvar_dados_tabelas(chave, res); 
            self._registrar_log("GERADOR_CLOUD", f"Gerou tabela {chave} para nuvem")
            messagebox.showinfo("Sucesso", f"Tabela {chave} atualizada no servidor!")
        except Exception as e: messagebox.showerror("Erro Crítico", f"Falha ao gerar/upload:\n{str(e)}")

    def gerar_padrao_local(self, grupo):
        self.salvar_estado_atual(); d = self.vars[grupo]; pl = d['plano'].get()
        chave = f"t_{('imovel' if grupo=='2011' else 'auto')}{grupo}_{('normal' if pl=='N' else pl)}"
        path = filedialog.asksaveasfilename(title=f"Salvar {chave} Local", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile=f"{chave}.json")
        if not path: return
        try:
            res = calcular_simulacao(grupo, pl, d['prazo'].get(), d['credito_ini'].get(), d['credito_fim'].get(), d['passo'].get())
            with open(path, 'w', encoding='utf-8') as f: json.dump(res, f, indent=4, ensure_ascii=False)
            self._registrar_log("GERADOR_LOCAL", f"Gerou tabela {chave} em {path}")
            messagebox.showinfo("Salvo", f"Tabela {chave} salva localmente!")
        except Exception as e: messagebox.showerror("Erro Crítico", f"{str(e)}")

    def gerar_especial(self):
        self.salvar_estado_atual(); d = self.vars['esp']; pl = d['plano_tipo'].get()
        map_s = {"N": "_normal", "L": "_L", "SL": "_SL"}
        chave = f"t_{d['id_tabela'].get().strip()}{map_s.get(pl, '')}"
        seg = d['seguro'].get()
        cat = "IMOVEL" if abs(seg - 0.059) < 0.001 else ("AUTO" if abs(seg - 0.084) < 0.001 else "OUTROS")
        meta = {"id": chave, "name": d['nome_real'].get(), "category": cat, "plan": pl, "taxaAdmin": d['adm'].get()/100, "fundoReserva": 0.03, "seguroPct": round(seg/100, 5), "maxLanceEmbutido": 0.25}
        try:
            res = calcular_simulacao("ESPECIAL", "CUSTOM", d['prazo'].get(), d['credito_ini'].get(), d['credito_fim'].get(), d['passo'].get(), custom_data={'fator': {"NORMAL":1.0,"LIGHT":0.75,"SUPERLIGHT":0.5}[pl], 'adm': d['adm'].get()/100, 'fundo': 0.03, 'seguro': seg/100})
            if d['apenas_csv'].get():
                for item in res:
                    for p in item['prazos']:
                        if 'parcela_SSV' in p: del p['parcela_SSV']
                        if 'parcela_CSV' in p: p['parcela'] = p.pop('parcela_CSV')
            salvar_dados_tabelas(chave, res, metadata_item=meta)
            self._registrar_log("GERADOR_ESPECIAL", f"Criou tabela {chave} na nuvem")
            messagebox.showinfo("Sucesso", f"Tabela Especial {chave} atualizada no servidor!")
        except Exception as e: messagebox.showerror("Erro Crítico", f"Falha ao gerar/upload:\n{str(e)}")

    def gerar_especial_local(self):
        self.salvar_estado_atual(); d = self.vars['esp']
        path = filedialog.asksaveasfilename(title=f"Salvar Especial Local", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile=f"tabela_especial.json")
        if not path: return
        pl = d['plano_tipo'].get(); seg = d['seguro'].get()
        try:
            res = calcular_simulacao("ESPECIAL", "CUSTOM", d['prazo'].get(), d['credito_ini'].get(), d['credito_fim'].get(), d['passo'].get(), custom_data={'fator': {"":1.0,"L":0.75,"SL":0.5}[pl], 'adm': d['adm'].get()/100, 'fundo': 0.03, 'seguro': seg/100})
            if d['apenas_csv'].get():
                for item in res:
                    for p in item['prazos']:
                        if 'parcela_SSV' in p: del p['parcela_SSV']
                        if 'parcela_CSV' in p: p['parcela'] = p.pop('parcela_CSV')
            with open(path, 'w', encoding='utf-8') as f: json.dump(res, f, indent=4, ensure_ascii=False)
            self._registrar_log("GERADOR_ESPECIAL_LOCAL", f"Salvou especial em {path}")
            messagebox.showinfo("Salvo", f"Tabela especial salva localmente!")
        except Exception as e: messagebox.showerror("Erro Crítico", f"{str(e)}")

def center_root(r):
    r.update_idletasks()
    w = r.winfo_screenwidth(); h = r.winfo_screenheight()
    size = tuple(int(_) for _ in r.geometry().split('+')[0].split('x'))
    x = w/2 - size[0]/2; y = h/2 - size[1]/2
    r.geometry("%dx%d+%d+%d" % (size + (x, y)))

def iniciar_aplicacao_principal(user, role): 
    app = ConsorcioApp(root, current_user_role=role, current_username=user)
    root.geometry("780x670")
    center_root(root)

if __name__ == "__main__":
    root = tk.Tk()
    
    from auth import AuthManager
    am = AuthManager()
    
    if not am.has_users():
        tk.messagebox.showwarning("Primeiro Acesso", "Nenhum usuário encontrado.\nUse 'admin_setup.py' para criar o primeiro ADMIN.")
        root.destroy()
    else:
        app_login = LoginWindow(root, iniciar_aplicacao_principal)
        root.mainloop()
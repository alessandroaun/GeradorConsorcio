import tkinter as tk
from tkinter import ttk, messagebox
from auth import AuthManager

COLOR_BG = "#F9FAFB"
COLOR_PRIMARY = "#2563EB"
COLOR_CARD = "#FFFFFF"
COLOR_TEXT_MAIN = "#111827"

class LoginWindow:
    def __init__(self, root, on_success_callback):
        self.root = root
        self.on_success = on_success_callback
        self.auth = AuthManager()
        
        self.root.title("Acesso Restrito")
        self.root.geometry("400x450")
        self.root.configure(bg=COLOR_BG)
        self.root.resizable(False, False)
        self._center_window()
        self._setup_ui()

    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def _setup_ui(self):
        # Limpa widgets anteriores (caso esteja recarregando a tela)
        for widget in self.root.winfo_children():
            widget.destroy()

        card = tk.Frame(self.root, bg=COLOR_CARD, padx=30, pady=30)
        card.place(relx=0.5, rely=0.5, anchor="center", width=340, height=380)

        tk.Label(card, text="Bem-vindo", font=("Segoe UI", 25, "bold"), bg=COLOR_CARD, fg=COLOR_PRIMARY).pack(pady=(0, 5))
        tk.Label(card, text="Faça login para continuar", font=("Segoe UI", 10), bg=COLOR_CARD, fg="#6B7280").pack(pady=(0, 25))

        tk.Label(card, text="Usuário", font=("Segoe UI", 9, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT_MAIN).pack(anchor="w")
        self.entry_user = ttk.Entry(card, font=("Segoe UI", 10))
        self.entry_user.pack(fill="x", pady=(5, 15))
        self.entry_user.focus()

        tk.Label(card, text="Senha", font=("Segoe UI", 9, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT_MAIN).pack(anchor="w")
        self.entry_pass = ttk.Entry(card, font=("Segoe UI", 10), show="*")
        self.entry_pass.pack(fill="x", pady=(5, 20))
        self.entry_pass.bind('<Return>', lambda e: self.do_login())

        tk.Button(card, text="ENTRAR", font=("Segoe UI", 10, "bold"), bg=COLOR_PRIMARY, fg="white", relief="flat", command=self.do_login).pack(fill="x", pady=10, ipady=5)
        # Rodapé
        tk.Label(card, text="Desenvolvido por Alessandro Uchoa", 
                 font=("Segoe UI", 8), bg=COLOR_CARD, fg="#9CA3AF").pack(side="bottom")

    def do_login(self):
        user = self.entry_user.get()
        password = self.entry_pass.get()

        if not user or not password:
            messagebox.showwarning("Atenção", "Preencha todos os campos.")
            return

        # Tenta autenticar
        # OBS: Se seu auth.py usar 'login' em vez de 'authenticate', altere o nome abaixo
        if hasattr(self.auth, 'authenticate'):
            success, role, reset_required = self.auth.authenticate(user, password)
        else:
            # Fallback caso esteja usando a versão do auth.py que passei anteriormente
            success, role, msg = self.auth.login(user, password)
            reset_required = False # Assumindo false se usar o método login antigo

        if success:
            if reset_required:
                # Intercepta e força a troca de senha
                self.show_force_change_password(user, role)
            else:
                # Login normal - CORREÇÃO AQUI: Passando 'user' e 'role'
                self.start_app(user, role)
        else:
            # Se a autenticação falhar, tenta pegar a mensagem de erro se disponível
            msg_erro = "Usuário ou senha incorretos."
            messagebox.showerror("Erro", msg_erro)

    def start_app(self, user, role):
        # Limpa a tela
        for widget in self.root.winfo_children():
            widget.destroy()
        # CORREÇÃO AQUI: Envia 'user' e 'role' para o app.py
        self.on_success(user, role)

    def show_force_change_password(self, user, role):
        """Tela intermediária obrigatória para troca de senha"""
        # Limpa o card de login
        for widget in self.root.winfo_children():
            widget.destroy()

        card = tk.Frame(self.root, bg=COLOR_CARD, padx=30, pady=30)
        card.place(relx=0.5, rely=0.5, anchor="center", width=340, height=400)

        tk.Label(card, text="Troca de Senha", font=("Segoe UI", 14, "bold"), bg=COLOR_CARD, fg=COLOR_PRIMARY).pack(pady=(0, 5))
        tk.Label(card, text="Por segurança, defina uma nova senha.", font=("Segoe UI", 9), bg=COLOR_CARD, fg="red").pack(pady=(0, 20))

        tk.Label(card, text="Nova Senha", font=("Segoe UI", 9, "bold"), bg=COLOR_CARD).pack(anchor="w")
        entry_new = ttk.Entry(card, show="*")
        entry_new.pack(fill="x", pady=(5, 15))
        entry_new.focus()

        tk.Label(card, text="Confirmar Senha", font=("Segoe UI", 9, "bold"), bg=COLOR_CARD).pack(anchor="w")
        entry_conf = ttk.Entry(card, show="*")
        entry_conf.pack(fill="x", pady=(5, 20))

        def save_new_password():
            p1 = entry_new.get().strip()
            p2 = entry_conf.get().strip()
            
            if not p1 or len(p1) < 4:
                messagebox.showwarning("Fraca", "A senha deve ter pelo menos 4 caracteres.")
                return
            if p1 != p2:
                messagebox.showerror("Erro", "As senhas não coincidem.")
                return

            # Chama a função de troca do usuário
            ok, msg = self.auth.user_change_password(user, p1)
            if ok:
                messagebox.showinfo("Sucesso", "Senha atualizada! Entrando no sistema...")
                # CORREÇÃO AQUI: Passando 'user' e 'role'
                self.start_app(user, role)
            else:
                messagebox.showerror("Erro", msg)

        tk.Button(card, text="SALVAR E ENTRAR", font=("Segoe UI", 10, "bold"), bg=COLOR_PRIMARY, fg="white", relief="flat", command=save_new_password).pack(fill="x", pady=10)
import os
import sys
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread

# --- CONFIGURAÇÃO ---
# Lembre-se de mudar isso antes de gerar o executável
CURRENT_VERSION = "1.0.3" 

# URL DO JSON NO SUPABASE
URL_VERSION_JSON = "https://nhnejoanmggvinnfphir.supabase.co/storage/v1/object/public/upadates/updates/version.json"
# (Certifique-se que o caminho acima está correto com o bucket que você criou)

class UpdateManager:
    def __init__(self, root):
        self.root = root

    def check_for_updates(self):
        """Verifica se há atualização (Lógica de Update Obrigatório)"""
        print("--- INICIANDO CHECAGEM DE UPDATE ---")
        try:
            # 1. Tenta baixar o JSON
            try:
                response = requests.get(URL_VERSION_JSON, timeout=10)
                response.raise_for_status() 
                data = response.json()
            except Exception as e:
                # Se falhar a internet ou o link, avisa mas deixa entrar (ou bloqueia, dependendo da sua escolha)
                # Por enquanto, vou deixar entrar se der erro de conexão para não travar a operação se a internet cair.
                print(f"Erro ao verificar updates: {e}")
                return False
            
            latest_version = data.get("version", "0.0.0")
            download_url = data.get("url", "")
            changelog = data.get("changelog", "")

            print(f"Versão Local: {CURRENT_VERSION} | Versão Remota: {latest_version}")

            # 2. Compara versões
            if latest_version != CURRENT_VERSION:
                if self._is_newer(latest_version, CURRENT_VERSION):
                    
                    # --- ALTERAÇÃO AQUI: UPDATE OBRIGATÓRIO ---
                    
                    # Exibe aviso (botão único OK)
                    messagebox.showwarning("Atualização Obrigatória", 
                                           f"Uma nova versão ({latest_version}) foi encontrada.\n\n"
                                           f"Mudanças:\n{changelog}\n\n"
                                           "É necessário atualizar para continuar utilizando o sistema.\n"
                                           "Clique em OK para iniciar a atualização.")
                    
                    # Não pergunta "Sim/Não", executa direto
                    self._download_and_install(download_url)
                    
                    return True # Retorna True para avisar o app.py que vai atualizar e deve fechar
                
            return False # Nenhuma atualização, segue o fluxo normal

        except Exception as e:
            messagebox.showerror("Erro no Update", f"Ocorreu um erro crítico ao verificar atualizações: {e}")
            return False

    def _is_newer(self, remote, local):
        """Compara versões X.Y.Z"""
        try:
            r_parts = [int(x) for x in remote.split('.')]
            l_parts = [int(x) for x in local.split('.')]
            return r_parts > l_parts
        except:
            return remote != local

    def _download_and_install(self, url):
        """Baixa e Executa"""
        top = tk.Toplevel(self.root)
        top.title("Atualizando Sistema...")
        top.geometry("300x150")
        top.resizable(False, False)
        
        # Remove o botão de fechar da janela (X) para impedir cancelamento fácil
        top.protocol("WM_DELETE_WINDOW", lambda: None)
        
        try:
            x = self.root.winfo_screenwidth() // 2 - 150
            y = self.root.winfo_screenheight() // 2 - 75
            top.geometry(f"+{x}+{y}")
        except: pass

        ttk.Label(top, text="Baixando atualização", font=("Segoe UI", 10, "bold"), foreground="red").pack(pady=10)
        progress = ttk.Progressbar(top, orient="horizontal", length=250, mode="determinate")
        progress.pack(pady=10)
        lbl_status = ttk.Label(top, text="Iniciando...", font=("Segoe UI", 8))
        lbl_status.pack()

        def _thread_dl():
            try:
                temp_dir = os.environ.get('TEMP', '.')
                installer_name = "Setup_Update_Recon.exe"
                save_path = os.path.join(temp_dir, installer_name)
                
                with requests.get(url, stream=True) as r:
                    r.raise_for_status()
                    total_length = int(r.headers.get('content-length', 0))
                    dl = 0
                    with open(save_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                dl += len(chunk)
                                f.write(chunk)
                                if total_length > 0:
                                    pct = int(100 * dl / total_length)
                                    top.after(0, lambda p=pct: (progress.config(value=p), lbl_status.config(text=f"{p}%")))
                
                top.after(0, lambda: self._launch_installer(save_path))

            except Exception as e:
                # Se der erro no download obrigatório, o app fecha. Não pode usar sem atualizar.
                top.after(0, lambda: messagebox.showerror("Erro Fatal", f"Falha ao baixar atualização: {e}\nO sistema será encerrado."))
                top.after(0, lambda: sys.exit(0))

        Thread(target=_thread_dl, daemon=True).start()
        
        # Trava a tela principal
        top.grab_set()
        self.root.wait_window(top)

    def _launch_installer(self, installer_path):
        """Executa o instalador e FECHA O APP"""
        try:
            if not os.path.exists(installer_path):
                messagebox.showerror("Erro", "O arquivo de atualização não foi encontrado.")
                sys.exit(0)

            os.startfile(installer_path)
            
            # Fecha o app Python IMEDIATAMENTE
            self.root.destroy()
            sys.exit(0)
            
        except Exception as e:
            messagebox.showerror("Erro Crítico", f"Não foi possível iniciar o instalador: {e}")
            sys.exit(0)
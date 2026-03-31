import os
import sys
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread

# --- CONFIGURAÇÃO ---
CURRENT_VERSION = "1.0.9" 

# URL DO JSON NO SUPABASE
# Atenção: Notei um erro de digitação no seu link original ("upadates"), mantive como você enviou, 
# mas verifique se no Supabase a pasta é 'updates' ou 'upadates'.
URL_VERSION_JSON = "https://nhnejoanmggvinnfphir.supabase.co/storage/v1/object/public/upadates/updates/version.json"

class UpdateManager:
    def __init__(self, root):
        self.root = root

    def check_for_updates(self):
        """Verifica se há atualização"""
        print("--- INICIANDO CHECAGEM DE UPDATE ---")
        try:
            try:
                response = requests.get(URL_VERSION_JSON, timeout=10)
                response.raise_for_status() 
                data = response.json()
            except Exception as e:
                print(f"Erro ao verificar updates: {e}")
                return False
            
            latest_version = data.get("version", "0.0.0")
            download_url = data.get("url", "")
            changelog = data.get("changelog", "")

            print(f"Versão Local: {CURRENT_VERSION} | Versão Remota: {latest_version}")

            if latest_version != CURRENT_VERSION:
                if self._is_newer(latest_version, CURRENT_VERSION):
                    messagebox.showwarning("Atualização Obrigatória", 
                                           f"Uma nova versão ({latest_version}) foi encontrada.\n\n"
                                           f"Mudanças:\n{changelog}\n\n"
                                           "É necessário atualizar para continuar utilizando o sistema.\n"
                                           "Clique em OK para iniciar a atualização.")
                    
                    self._download_and_install(download_url)
                    return True 
                
            return False 

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
        top.geometry("350x150")
        top.resizable(False, False)
        
        # Centralizar
        try:
            x = self.root.winfo_screenwidth() // 2 - 175
            y = self.root.winfo_screenheight() // 2 - 75
            top.geometry(f"+{x}+{y}")
        except: pass

        # Impede fechar a janela
        top.protocol("WM_DELETE_WINDOW", lambda: None)
        
        lbl_info = ttk.Label(top, text="Baixando atualização...", font=("Segoe UI", 10, "bold"), foreground="blue")
        lbl_info.pack(pady=(15, 5))

        # Barra de progresso
        progress = ttk.Progressbar(top, orient="horizontal", length=300, mode="determinate")
        progress.pack(pady=5)
        
        lbl_status = ttk.Label(top, text="0%", font=("Segoe UI", 9))
        lbl_status.pack(pady=2)

        def _thread_dl():
            try:
                temp_dir = os.environ.get('TEMP', '.')
                installer_name = "Setup_Update_Recon.exe"
                save_path = os.path.join(temp_dir, installer_name)
                
                with requests.get(url, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    total_length = int(r.headers.get('content-length', 0))
                    
                    dl = 0
                    last_pct = -1
                    
                    with open(save_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                dl += len(chunk)
                                f.write(chunk)
                                
                                # Atualiza a barra apenas se tiver tamanho total definido
                                if total_length > 0:
                                    pct = int(100 * dl / total_length)
                                    # Só atualiza a UI se a porcentagem mudou para não travar
                                    if pct > last_pct:
                                        last_pct = pct
                                        top.after(0, lambda p=pct: (progress.config(value=p), lbl_status.config(text=f"{p}%")))
                                else:
                                    # Se o servidor não der o tamanho, deixa em modo indeterminado
                                    top.after(0, lambda: progress.config(mode='indeterminate'))
                                    top.after(0, lambda: progress.start(10))

                top.after(0, lambda: lbl_info.config(text="Iniciando Instalador..."))
                top.after(1000, lambda: self._launch_installer(save_path))

            except Exception as e:
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
            
            # Fecha o app Python IMEDIATAMENTE E FORÇADO
            self.root.destroy()
            os._exit(0) # Força bruta para fechar, garantindo que não fique nada na memória
            
        except Exception as e:
            messagebox.showerror("Erro Crítico", f"Não foi possível iniciar o instalador: {e}")
            sys.exit(0)
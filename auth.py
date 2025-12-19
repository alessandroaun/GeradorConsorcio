import os
import json
import bcrypt
from cryptography.fernet import Fernet
import sys
from json_utils import supabase, BUCKET_NAME

KEY_FILE = "secret.key"
DB_FILE = "users.dat"

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class AuthManager:
    def __init__(self):
        self.base_path = get_base_path()
        self.key_path = os.path.join(self.base_path, KEY_FILE)
        self.db_path = os.path.join(self.base_path, DB_FILE)
        self._sync_download()
        self.key = self._load_or_generate_key()
        self.cipher = Fernet(self.key)

    def _sync_download(self):
        try:
            try:
                data_key = supabase.storage.from_(BUCKET_NAME).download(KEY_FILE)
                with open(self.key_path, "wb") as f: f.write(data_key)
            except: pass
            try:
                data_db = supabase.storage.from_(BUCKET_NAME).download(DB_FILE)
                with open(self.db_path, "wb") as f: f.write(data_db)
            except: pass
        except: pass

    def _sync_upload(self):
        try:
            with open(self.key_path, "rb") as f:
                supabase.storage.from_(BUCKET_NAME).upload(KEY_FILE, f, file_options={"upsert": "true"})
            with open(self.db_path, "rb") as f:
                supabase.storage.from_(BUCKET_NAME).upload(DB_FILE, f, file_options={"upsert": "true"})
            return True
        except: return False

    def _load_or_generate_key(self):
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as kf: return kf.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_path, "wb") as kf: kf.write(key)
            self._sync_upload()
            return key

    def _save_db(self, data):
        json_data = json.dumps(data).encode('utf-8')
        encrypted_data = self.cipher.encrypt(json_data)
        with open(self.db_path, "wb") as f: f.write(encrypted_data)

    def _load_db(self):
        if not os.path.exists(self.db_path): return {}
        try:
            with open(self.db_path, "rb") as f: encrypted_data = f.read()
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))
        except: return {}

    # --- FUNÇÕES DE USUÁRIO ---

    def create_user(self, username, password, role="user"):
        users = self._load_db()
        if username in users: return False, "Usuário já existe."
        
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        users[username] = {
            "password": hashed.decode('utf-8'),
            "role": role,
            "reset_required": True  # <--- MARCA OBRIGATÓRIO NA CRIAÇÃO
        }
        
        self._save_db(users)
        self._sync_upload()
        return True, "Criado com sucesso (Primeiro acesso exigirá troca de senha)."

    def delete_user(self, username):
        users = self._load_db()
        if username not in users: return False, "Não encontrado."
        del users[username]
        self._save_db(users)
        self._sync_upload()
        return True, "Removido com sucesso."

    def admin_reset_password(self, username):
        """ADMIN: Reseta senha para '12345' e força troca."""
        users = self._load_db()
        if username not in users: return False, "Usuário não encontrado."
        
        # Senha padrão 12345
        default_pw = "12345"
        hashed = bcrypt.hashpw(default_pw.encode('utf-8'), bcrypt.gensalt())
        
        users[username]["password"] = hashed.decode('utf-8')
        users[username]["reset_required"] = True # Força a troca
        
        self._save_db(users)
        self._sync_upload()
        return True, f"Senha de '{username}' resetada para '12345'."

    def user_change_password(self, username, new_password):
        """USUÁRIO: Troca a própria senha e remove a flag."""
        users = self._load_db()
        if username not in users: return False, "Erro crítico: Usuário sumiu."
        
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        users[username]["password"] = hashed.decode('utf-8')
        users[username]["reset_required"] = False # Remove a obrigatoriedade
        
        self._save_db(users)
        self._sync_upload()
        return True, "Senha alterada com sucesso!"

    def authenticate(self, username, password):
        users = self._load_db()
        if username not in users: return False, None, False
        
        user_data = users[username]
        # Compatibilidade com versões antigas do JSON
        if isinstance(user_data, str): 
            stored_hash = user_data.encode('utf-8')
            role = "admin"
            reset_req = False
        else:
            stored_hash = user_data["password"].encode('utf-8')
            role = user_data.get("role", "user")
            reset_req = user_data.get("reset_required", False) # Verifica a flag

        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            return True, role, reset_req # Retorna se precisa resetar
        return False, None, False

    def has_users(self):
        return len(self._load_db()) > 0
    
    def get_users_list(self):
        return list(self._load_db().keys())
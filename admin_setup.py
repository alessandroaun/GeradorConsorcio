from auth import AuthManager
import getpass

def main():
    print("--- CRIAR PRIMEIRO ADMINISTRADOR ---")
    auth = AuthManager()
    
    user = input("Usuário (ex: admin): ").strip()
    pwd = getpass.getpass("Senha: ").strip()
    confirm = getpass.getpass("Confirmar: ").strip()
    
    if pwd != confirm:
        print("Senhas não conferem.")
        return

    # Força role='admin'
    success, msg = auth.create_user(user, pwd, role="admin")
    print(f"Resultado: {msg}")

if __name__ == "__main__":
    main()
import flet as ft
from models import User, session_scope 

# A assinatura tem 5 argumentos
def show_login(page, state, go_to_home_func, go_to_register_func, show_snack_func):
    page.controls.clear()
    
    username = ft.TextField(label="Usuário")
    password = ft.TextField(label="Senha", password=True, can_reveal_password=True)
    msg = ft.Text("", color=ft.Colors.RED)

    def do_login(ev):
            uname = username.value.strip()
            pwd = password.value.strip() # Adicionando strip() para segurança
            
            if not uname:
                msg.value = "Insira o nome de usuário"
                page.update() 
                return
                
            try:
                with session_scope() as s:
                    user = s.query(User).filter_by(username=uname).first()
                    
                    if user and user.check_password(pwd):
                        # Caminho de SUCESSO
                        state["current_user"] = {"id": user.id, "username": user.username}
                        show_snack_func(f"Bem-vindo, {user.username}!")
                        go_to_home_func() # Navega para a Home
                    else:
                        # Caminho de FALHA na autenticação
                        msg.value = "Usuário ou senha inválidos"
                        page.update()
                        
            except Exception as e:
                print(f"Erro de Login: {e}") 
                msg.value = "Ocorreu um erro interno ao tentar logar. Verifique o console."
                page.update()

    page.add(ft.Text("Login", size=20), username, password,
             ft.Row([ft.ElevatedButton("Log-in", on_click=do_login),
                     # CORREÇÃO: Envolver go_to_register_func em um lambda para ignorar o evento 'e'
                     ft.TextButton("Não tenho uma conta", on_click=lambda e: go_to_register_func())]), msg)
    page.update()
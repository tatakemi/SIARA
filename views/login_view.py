import flet as ft
from models import User, session_scope #

def login_view(page, state, go_to_home_func, go_to_register_func, show_snack_func):
    page.controls.clear()
    
    username = ft.TextField(label="Usuário")
    password = ft.TextField(label="Senha", password=True, can_reveal_password=True)
    msg = ft.Text("", color=ft.Colors.RED)

    def do_login(ev):
        uname = username.value.strip()
        pwd = password.value or ""
        if not uname:
            msg.value = "Insira o nome de usuário"
            page.update()
            return
        with session_scope() as s:
            user = s.query(User).filter_by(username=uname).first() #
            if user and user.check_password(pwd):
                state["current_user"] = {"id": user.id, "username": user.username}
                go_to_home_func() # Usa a função de navegação injetada
            else:
                msg.value = "Usuário ou senha inválidos"
                page.update()

    page.add(ft.Text("Login", size=20), username, password,
             ft.Row([ft.ElevatedButton("Log-in", on_click=do_login),
                     ft.TextButton("Não tenho uma conta", on_click=go_to_register_func)]), msg)
    page.update()

show_login = login_view
import flet as ft
from models import User, session_scope #

def register_view(page, state, go_to_home_func, go_to_login_func, show_snack_func):
    page.controls.clear()
    
    username = ft.TextField(label="Usuário")
    contact = ft.TextField(label="Contato (telefone/email)")
    password = ft.TextField(label="Senha", password=True, can_reveal_password=True)
    password2 = ft.TextField(label="Confirmar senha", password=True, can_reveal_password=True)
    msg = ft.Text("", color=ft.Colors.RED)

    def do_register(ev):
        uname = username.value.strip()
        pwd = password.value or ""
        pwd2 = password2.value or ""
        if pwd != pwd2 or not pwd:
            msg.value = "As senhas não coincidem ou estão vazias"
            page.update()
            return
        with session_scope() as s: #
            existing = s.query(User).filter_by(username=uname).first() #
            if existing:
                msg.value = "Usuário já existe"
                page.update()
                return
            u = User(username=uname, contact=contact.value.strip())
            u.set_password(pwd)
            s.add(u)
            s.flush()
            state["current_user"] = {"id": u.id, "username": u.username}
        show_snack_func("Conta criada. Você está logado.")
        go_to_home_func() 
        
    page.add(ft.Text("Registro", size=20), username, contact, password, password2,
             ft.Row([ft.ElevatedButton("Registrar", on_click=do_register),
                     ft.TextButton("Voltar para Login", on_click=go_to_login_func)]), msg)
    page.update()

show_register = register_view
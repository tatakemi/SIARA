# views/register_view.py
import flet as ft
from models import User, session_scope

class RegisterView(ft.UserControl):
    """View para a tela de Registro de novo usuário."""
    def __init__(self, page, state, show_snack, show_home, show_login):
        super().__init__()
        self.page = page
        self.state = state
        self.show_snack = show_snack
        self.show_home = show_home
        self.show_login = show_login
        
        self.username = ft.TextField(label="Usuário")
        self.contact = ft.TextField(label="Contato (telefone/email)")
        self.password = ft.TextField(label="Senha", password=True, can_reveal_password=True)
        self.password2 = ft.TextField(label="Confirmar senha", password=True, can_reveal_password=True)
        self.msg = ft.Text("", color=ft.Colors.RED)

    def do_register(self, e):
        uname = self.username.value.strip()
        pwd = self.password.value or ""
        pwd2 = self.password2.value or ""
        if not uname:
            self.msg.value = "Insira o nome de usuário"
            self.update()
            return
        if pwd != pwd2 or not pwd:
            self.msg.value = "As senhas não coincidem ou estão vazias"
            self.update()
            return
        
        with session_scope() as s:
            existing = s.query(User).filter_by(username=uname).first()
            if existing:
                self.msg.value = "Usuário já existe"
                self.update()
                return
            u = User(username=uname, contact=self.contact.value.strip())
            u.set_password(pwd)
            s.add(u)
            s.flush()
            self.state["current_user"] = {"id": u.id, "username": u.username}
        
        self.show_snack("Account created; you are now logged in.")
        self.show_home()

    def build(self):
        return ft.Column([
            ft.Text("Registro de Usuário", size=20),
            self.username,
            self.contact,
            self.password,
            self.password2,
            ft.Row([
                ft.ElevatedButton("Registrar", on_click=self.do_register),
                ft.TextButton("Já tenho uma conta", on_click=self.show_login)
            ]),
            self.msg
        ])
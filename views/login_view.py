# views/login_view.py
import flet as ft
from models import User, session_scope

class LoginView(ft.UserControl):
    """View para a tela de Login."""
    def __init__(self, page, state, show_snack, show_home, show_register):
        super().__init__()
        self.page = page
        self.state = state
        self.show_snack = show_snack
        self.show_home = show_home
        self.show_register = show_register
        
        self.username = ft.TextField(label="Usuário")
        self.password = ft.TextField(label="Senha", password=True, can_reveal_password=True)
        self.msg = ft.Text("", color=ft.Colors.RED)

    def do_login(self, e):
        uname = self.username.value.strip()
        pwd = self.password.value or ""
        if not uname:
            self.msg.value = "Insira o nome de usuário"
            self.update()
            return
        
        with session_scope() as s:
            user = s.query(User).filter_by(username=uname).first()
            if user and user.check_password(pwd):
                self.state["current_user"] = {"id": user.id, "username": user.username}
                self.show_home()
            else:
                self.msg.value = "Usuário ou senha inválidos"
                self.update()

    def build(self):
        return ft.Column([
            ft.Text("Login", size=20), 
            self.username, 
            self.password,
            ft.Row([
                ft.ElevatedButton("Log-in", on_click=self.do_login),
                ft.TextButton("Não tenho uma conta", on_click=self.show_register)
            ]), 
            self.msg
        ])
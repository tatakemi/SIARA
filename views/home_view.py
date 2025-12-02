# views/home_view.py
import flet as ft
from models import LostAnimal, FoundReport, session_scope

class HomeView(ft.UserControl):
    """View para a tela principal, mostrando a lista de posts globais."""
    def __init__(self, page, state, show_snack, show_login, show_lost_reg, show_found_reg, show_my_posts, show_map):
        super().__init__()
        self.page = page
        self.state = state
        self.show_snack = show_snack
        self.show_login = show_login
        self.show_lost_reg = show_lost_reg
        self.show_found_reg = show_found_reg
        self.show_my_posts = show_my_posts
        self.show_map = show_map

    def do_logout(self, e):
        self.state["current_user"] = None
        self.show_login()

    def build(self):
        cur = self.state["current_user"]
        if not cur:
            # Caso o usuário não esteja logado, redireciona para o login
            self.show_login() 
            return ft.Container(ft.Text("Redirecionando...")) # Retorna um placeholder

        header = ft.Text(f"Bem-vindo(a), {cur['username']}", size=18)
        
        btn_lost = ft.ElevatedButton("Registrar animal perdido", on_click=self.show_lost_reg)
        btn_found = ft.ElevatedButton("Registrar animal encontrado", on_click=self.show_found_reg)
        btn_my = ft.ElevatedButton("Meus posts", on_click=self.show_my_posts)
        btn_map = ft.ElevatedButton("Abrir mapa (browser)", on_click=self.show_map)
        btn_logout = ft.TextButton("Sair", on_click=self.do_logout)

        lost_list = ft.ListView(expand=True, spacing=10)
        found_list = ft.ListView(expand=True, spacing=10)

        with session_scope() as s:
            # Popula a lista de animais perdidos
            for a in s.query(LostAnimal).order_by(LostAnimal.id.desc()).all():
                owner_name = a.owner.username if a.owner else "—"
                info = f"Tutor: {owner_name}\nOnde foi perdido: {a.lost_location or ''}\nDescrição: {a.desc_animal or ''}"
                if a.latitude and a.longitude:
                    info += f"\nCoordenadas: {a.latitude:.6f}, {a.longitude:.6f}"
                lost_list.controls.append(ft.Container(ft.ListTile(title=ft.Text(a.name), subtitle=ft.Text(info)), bgcolor=ft.Colors.BLACK12, padding=12, margin=3, border_radius=8))
            
            # Popula a lista de relatórios de encontrados
            for r in s.query(FoundReport).order_by(FoundReport.id.desc()).all():
                finder_name = r.finder.username if r.finder else "—"
                info = f"Quem encontrou: {finder_name}\nOnde foi encontrado: {r.found_location or ''}\nDescrição: {r.found_description or ''}"
                if r.latitude and r.longitude:
                    info += f"\nCoordenadas: {r.latitude:.6f}, {r.longitude:.6f}"
                found_list.controls.append(ft.Container(ft.ListTile(title=ft.Text(r.species or "Animal encontrado"), subtitle=ft.Text(info)), bgcolor=ft.Colors.INDIGO_ACCENT, padding=12, margin=3, border_radius=8))

        return ft.Column([
            header,
            ft.Row([btn_lost, btn_found, btn_my, btn_map, btn_logout]),
            ft.Text("Animais perdidos:"), 
            lost_list, 
            ft.Text("Animais encontrados:"), 
            found_list
        ])
# views/map_view.py
import flet as ft
import webbrowser
from services.map_server import LAST_PICK

class MapView(ft.UserControl):
    """View para a tela de Abertura do Mapa e confirmação de coordenadas."""
    def __init__(self, page, state, show_home):
        super().__init__()
        self.page = page
        self.state = state
        self.show_home = show_home
        
    def open_browser_map(self, e):
        port = self.state["map_port"]
        map_url = f"http://127.0.0.1:{port}/map.html"
        try:
            webbrowser.open(map_url)
        except Exception as ex:
            print("Failed to open browser:", ex)
        
    def build(self):
        port = self.state["map_port"]
        map_url = f"http://127.0.0.1:{port}/map.html"
        
        # Abre o mapa no navegador assim que a view é carregada
        # (Optei por manter a chamada no botão também, para reabertura)
        self.open_browser_map(None) 
        
        return ft.Column([
            ft.Text("Mapa aberto no seu navegador", size=18),
            ft.Text("Clique no mapa, retorne ao app e então clique em 'Atualizar coordenadas' no formulário de registro.", selectable=True),
            ft.Row([
                ft.ElevatedButton("Voltar", on_click=self.show_home),
                ft.ElevatedButton("Abrir mapa no navegador", on_click=self.open_browser_map)
            ]),
            ft.Text(f"Map URL: {map_url}", selectable=True)
        ])
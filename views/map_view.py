import flet as ft
import webbrowser

def map_view(page, state, go_to_home_func):
    page.controls.clear()
    
    port = state.get("map_port")
    if not port:
        page.add(ft.Text("Erro: Servidor de mapa não inicializado.", color=ft.Colors.RED), 
                 ft.ElevatedButton("Voltar", on_click=go_to_home_func))
        page.update()
        return

    map_url = f"http://127.0.0.1:{port}/map.html"
    
    def open_map_browser(e):
        try:
            webbrowser.open(map_url)
        except Exception as ex:
            print("Failed to open browser:", ex)

    page.add(ft.Text("Mapa aberto no seu navegador", size=18),
             ft.Text(f"URL: {map_url}", selectable=True),
             ft.Text("Clique no mapa para marcar uma localização. As coordenadas serão enviadas de volta para o app.", selectable=True),
             ft.Row([ft.ElevatedButton("Voltar", on_click=go_to_home_func),
                     ft.ElevatedButton("Abrir Mapa no Navegador", on_click=open_map_browser)]),
             )
    page.update()

show_map = map_view
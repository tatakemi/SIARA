# app.py (Router Central e Orquestrador)
import flet as ft
from functools import partial

# Importa a lógica de banco de dados (Necessária para a função show_snack e setup)
from models import session_scope 

# Importa o Servidor do Mapa para iniciar/parar (Funções de Setup)
from services.map_server import (
    find_free_port, start_map_server, stop_map_server, 
    write_base_map_html
)

# ************************************************************
# 1. IMPORTAÇÃO DAS VIEWS MODULARIZADAS
# ************************************************************
from views.login_view import show_login
from views.register_view import show_register
from views.home_view import show_home
from views.my_posts_view import show_my_posts
from views.lost_registration_view import show_lost_registration
from views.found_registration_view import show_found_registration
from views.map_view import show_map


def main(page: ft.Page):
    # ---- 2. Configuração da Página e Estado ----
    page.title = "SIARA - Sistema de Localização de Animais"
    page.window_width = 1000
    page.window_height = 700
    page.padding = 20

    state = {"current_user": None, "map_port": None}

    # ---- 3. Utilitários de Feedback (show_snack) ----
    def show_snack(message: str, success: bool = True):
        color = ft.Colors.GREEN if success else ft.Colors.RED
        page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    # ---- 4. Definição das Funções de Navegação (Rotas) ----
    # Definir stubs (lambdas vazias) primeiro para que as funções possam se chamar
    # mutuamente sem erro de referência circular.

    go_to_login = lambda e=None: None
    go_to_register = lambda e=None: None
    go_to_home = lambda e=None: None
    go_to_lost_reg = lambda e=None: None
    go_to_found_reg = lambda e=None: None
    go_to_my_posts = lambda e=None: None
    go_to_map = lambda e=None: None

    # Atribuição do corpo das lambdas (Injeção de Dependência)
    # O 'partial' cria uma nova função que já tem os argumentos fixos (page, state, etc.)
    go_to_login = partial(show_login, page, state, go_to_home, go_to_register, show_snack)
    go_to_register = partial(show_register, page, state, go_to_home, go_to_login, show_snack)
    go_to_lost_reg = partial(show_lost_registration, page, state, go_to_home, show_snack)
    go_to_found_reg = partial(show_found_registration, page, state, go_to_home, show_snack)
    go_to_my_posts = partial(show_my_posts, page, state, go_to_home, show_snack)
    go_to_map = partial(show_map, page, state, go_to_home)
    
    # A home é a mais complexa, pois precisa de todas as outras rotas
    go_to_home = partial(show_home, page, state, go_to_login, go_to_lost_reg, go_to_found_reg, go_to_my_posts, go_to_map)

    # ---- 5. Inicialização dos Serviços ----
    write_base_map_html()
    if state.get("map_port") is None:
        port = find_free_port()
        state["map_port"] = port
        start_map_server(port)

    # Função para parar o servidor ao fechar a janela
    def on_page_close(e):
        print("Stopping map server...")
        stop_map_server()
    page.on_close = on_page_close
    
    # ---- 6. Início da UI ----
    # Sempre começa pela tela de login (ou home, se houver usuário persistido)
    if state["current_user"]:
        go_to_home()
    else:
        go_to_login()

if __name__ == "__main__":
    ft.app(target=main)
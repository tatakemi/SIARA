# app.py
import flet as ft
import webbrowser
import os
import threading
import socket
import json
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial
from contextlib import contextmanager
from models import User, LostAnimal, FoundReport, session_scope

# ************************************************************
# 1. IMPORTAÇÃO DE DEPENDÊNCIAS
# ************************************************************

from models import User, LostAnimal, FoundReport, session_scope 
from services.geocoding import geocode_address # Exemplo de importação
from services.map_server import (
    find_free_port, start_map_server, stop_map_server, 
    write_base_map_html, LAST_PICK
)

# Importação das VIEWS
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
    page.on_disconnect = lambda e: stop_map_server() 
    page.on_close = lambda e: stop_map_server()
    page.theme_mode = ft.ThemeMode.LIGHT

    # Estado compartilhado
    state = {
        "current_user": None, 
        "map_port": None,
        "edit_lost_id": None, 
        "edit_found_id": None 
    }

    # ---- 3. Utilitários e Funções Auxiliares ----

    def show_snack(message, is_error=False):
        """Exibe uma snackbar (notificação) na parte inferior da tela."""
        page.snack_bar = ft.SnackBar(
            ft.Text(message),
            bgcolor=ft.Colors.RED_600 if is_error else ft.Colors.GREEN_600,
            duration=3000
        )
        page.snack_bar.open = True
        page.update()

    def do_logout(e=None):
        """Limpa o estado do usuário e navega para a tela de Login."""
        state["current_user"] = None
        go_to_login() 
        show_snack("Sessão encerrada.", is_error=True)

    # ---- 4. Handlers de Ação (Edição e Exclusão) ----
    # Essa é a seção corrigida na primeira interação.

    def _handle_edit_post_logic(item_id, is_lost):
        """Define o ID do item a ser editado no estado e navega para o formulário de registro."""
        state["edit_lost_id"] = None
        state["edit_found_id"] = None
        
        if is_lost:
            state["edit_lost_id"] = item_id
            route_logics['lost_reg']() 
        else:
            state["edit_found_id"] = item_id
            route_logics['found_reg']() 

    def create_edit_handler(item_id, is_lost):
        """Cria o handler de click para o botão Editar."""
        return lambda e: _handle_edit_post_logic(item_id, is_lost)
        
    def _handle_delete_post_logic(item_id, is_lost):
        """Exclui o post e recarrega a tela de Meus Posts."""
        try:
            with session_scope() as s:
                current_user_id = state["current_user"]["id"]
                
                if is_lost:
                    s.query(LostAnimal).filter_by(id=item_id, owner_id=current_user_id).delete()
                    show_snack("Animal perdido excluído com sucesso.")
                else:
                    s.query(FoundReport).filter_by(id=item_id, finder_id=current_user_id).delete()
                    show_snack("Relato de animal encontrado excluído com sucesso.")
            
            # Recarrega a view de posts
            route_logics['my_posts']() 
        except Exception as ex:
            print(f"Erro ao excluir postagem: {ex}")
            show_snack("Erro ao excluir postagem. Verifique se o item existe.", is_error=True)

    def create_delete_handler(item_id, is_lost):
        return lambda e: _handle_delete_post_logic(item_id, is_lost)

    # ---- 5. Definição das Funções de Navegação (Router) ----

    route_logics = {}

    go_to_login = lambda e=None: route_logics['login']()
    go_to_register = lambda e=None: route_logics['register']()
    go_to_home = lambda e=None: route_logics['home']()
    go_to_lost_reg = lambda e=None: route_logics['lost_reg']()
    go_to_found_reg = lambda e=None: route_logics['found_reg']()
    go_to_my_posts = lambda e=None: route_logics['my_posts']()
    go_to_map = lambda e=None: route_logics['map']()

    route_logics['login'] = partial(show_login, page, state, go_to_home, go_to_register, show_snack)
    route_logics['register'] = partial(show_register, page, state, go_to_home, go_to_login, show_snack)
    route_logics['my_posts'] = partial(
        show_my_posts, 
        page, 
        state, 
        go_to_home, 
        create_edit_handler,   
        create_delete_handler, 
        show_snack             
    )
    route_logics['lost_reg'] = partial(show_lost_registration, page, state, go_to_home, show_snack)
    route_logics['found_reg'] = partial(show_found_registration, page, state, go_to_home, show_snack)
    route_logics['map'] = partial(show_map, page, state, go_to_home)
    route_logics['home'] = partial(
        show_home, 
        page, 
        state, 
        go_to_login, 
        go_to_lost_reg, 
        go_to_found_reg, 
        go_to_my_posts, 
        go_to_map, 
        do_logout
    )

    # ---- 6. Inicialização dos Serviços e Rota Inicial ----
    
    write_base_map_html()
    if state.get("map_port") is None:
        port = find_free_port()
        state["map_port"] = port
        start_map_server(port)
        
    go_to_login()


if __name__ == "__main__":
    ft.app(target=main)
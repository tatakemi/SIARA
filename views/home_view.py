import flet as ft
from models import LostAnimal, FoundReport, session_scope
from sqlalchemy import or_
# Importa a função de card (AGORA ATUALIZADA - que requer 'page')
from views.my_posts_view import build_post_card 

# A assinatura AGORA tem 8 argumentos
def show_home(page, state, go_to_login_func, go_to_lost_reg_func, go_to_found_reg_func, go_to_my_posts_func, go_to_map_func, do_logout_func):
    page.controls.clear()
    cur = state.get("current_user")
    
    # 1. Se não houver usuário logado, retorna para o login
    if not cur:
        go_to_login_func() 
        return

    # Lista de controles para exibir os posts
    posts_list = ft.ListView(expand=1, spacing=10, padding=20)
    
    # --- CONTROLES DE FILTRO ---
    search_field = ft.TextField(label="Buscar por Descrição ou Local", width=300)
    
    # Assumindo que você tem uma lista de espécies únicas
    species_options = ["Qualquer", "Cachorro", "Gato", "Pássaro", "Outro"] 
    species_dropdown = ft.Dropdown(
        label="Espécie",
        options=[ft.dropdown.Option(s) for s in species_options],
        width=150,
        value="Qualquer"
    )
    
    type_dropdown = ft.Dropdown(
        label="Tipo",
        options=[
            ft.dropdown.Option("Qualquer"),
            ft.dropdown.Option("Perdido"),
            ft.dropdown.Option("Encontrado"),
        ],
        width=150,
        value="Qualquer"
    )

    # --- FUNÇÃO PARA CARREGAR E EXIBIR OS POSTS (LÓGICA DE FILTRO) ---
    def load_and_display_posts(search_term="", species_filter="", type_filter=""):
        posts_list.controls.clear()
        
        # Converte para minúsculas para busca insensível a maiúsculas/minúsculas
        search_term = search_term.lower()
        species_filter = species_filter.lower()
        type_filter = type_filter.lower()
        
        try:
            with session_scope() as s:
                # 4.1. Carregar todos os posts
                lost_animals = s.query(LostAnimal).all()
                found_reports = s.query(FoundReport).all()
                
                all_posts = []

                # Lógica de Filtro
                def passes_filter(post, is_lost):
                    # Filtro por tipo (Perdido/Encontrado)
                    current_type = "perdido" if is_lost else "encontrado"
                    if type_filter != "qualquer" and type_filter != current_type: 
                        return False
                    
                    # Filtro por espécie
                    post_species = post.species.lower() if post.species else ""
                    if species_filter != "qualquer" and species_filter not in post_species:
                        return False

                    # Filtro de busca (Descrição/Localização)
                    if search_term:
                        desc = post.desc_animal.lower() if is_lost and post.desc_animal else post.found_description.lower() if not is_lost and post.found_description else ""
                        loc = post.lost_location.lower() if is_lost and post.lost_location else post.found_location.lower() if not is_lost and post.found_location else ""
                        
                        if search_term not in desc and search_term not in loc:
                            return False
                    
                    return True # Passou em todos os filtros

                
                # Aplica filtros e prepara cards
                for a in lost_animals:
                    if passes_filter(a, is_lost=True):
                        # CHAMADA CORRIGIDA: Passando 'page'
                        card = build_post_card(
                            page, # <--- CORREÇÃO AQUI: O primeiro argumento é 'page'
                            title=a.name or "Animal perdido",
                            location_text=a.lost_location,
                            description=a.desc_animal,
                            lat=a.latitude,
                            lon=a.longitude,
                            is_lost=True,
                            item_id=a.id,
                            on_edit_click=None, # Feed global não tem edição/exclusão
                            on_delete_click=None,
                            image_url=a.image_url 
                        )
                        posts_list.controls.append(card)

                for r in found_reports:
                    if passes_filter(r, is_lost=False):
                        # CHAMADA CORRIGIDA: Passando 'page'
                        card = build_post_card(
                            page, # <--- CORREÇÃO AQUI: O primeiro argumento é 'page'
                            title=r.species or "Animal encontrado",
                            location_text=r.found_location,
                            description=r.found_description,
                            lat=r.latitude,
                            lon=r.longitude,
                            is_lost=False,
                            item_id=r.id,
                            on_edit_click=None,
                            on_delete_click=None,
                            image_url=r.image_url 
                        )
                        posts_list.controls.append(card)

                if not posts_list.controls:
                    posts_list.controls.append(ft.Text("Nenhum registro encontrado com os filtros aplicados."))
            
        except Exception as e:
            posts_list.controls.append(ft.Text(f"Erro ao carregar posts: {e}", color=ft.Colors.RED))
            print(f"Erro ao carregar posts no home_view: {e}")
            
        page.update()

    def apply_filters(e):
        load_and_display_posts(search_field.value, species_dropdown.value, type_dropdown.value)
    
    # O Row que contém os controles de busca
    search_controls = ft.Row([
        search_field,
        species_dropdown,
        type_dropdown,
        ft.IconButton(
            icon=ft.Icons.SEARCH, 
            tooltip="Buscar/Aplicar Filtros",
            on_click=apply_filters
        ),
        ft.IconButton(
            icon=ft.Icons.REFRESH, 
            tooltip="Limpar Filtros",
            on_click=lambda e: (
                search_field.set_value(""), 
                species_dropdown.set_value("Qualquer"), 
                type_dropdown.set_value("Qualquer"), 
                apply_filters(e)
            )
        )
    ], alignment=ft.MainAxisAlignment.START, wrap=True)


    # 2. Definição do cabeçalho com o botão de Logout
    header = ft.Row([
        ft.Text(f"Bem-vindo, {cur['username']}!", size=24, weight=ft.FontWeight.BOLD),
        # Usa o novo argumento 'do_logout_func'
        ft.ElevatedButton("Logout", on_click=do_logout_func, 
                          style=ft.ButtonStyle(bgcolor=ft.Colors.RED_400, color=ft.Colors.WHITE))
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    
    # 3. Definição dos botões de navegação
    navigation_buttons = ft.Row(
        [
            ft.ElevatedButton("Cadastrar Animal Perdido", on_click=go_to_lost_reg_func),
            ft.ElevatedButton("Relatar Animal Encontrado", on_click=go_to_found_reg_func),
            ft.ElevatedButton("Meus Posts", on_click=go_to_my_posts_func),
            ft.ElevatedButton("Ver Mapa", on_click=go_to_map_func),
        ],
        wrap=True,
        alignment=ft.MainAxisAlignment.CENTER
    )

    # 4. Adição dos controles à página
    page.add(
        header,
        ft.Divider(),
        navigation_buttons,
        ft.Text("Feed Global de Registros (Perdidos e Encontrados)", size=18, weight=ft.FontWeight.BOLD),
        ft.Divider(height=10),
        search_controls,
        ft.Divider(height=10),
        posts_list # O ListView para exibir os posts
    )
    
    # Carrega os posts iniciais (sem filtro)
    load_and_display_posts(search_field.value, species_dropdown.value, type_dropdown.value)
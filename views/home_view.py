import flet as ft
from models import LostAnimal, FoundReport, session_scope
# Importa a função de card (AGORA ATUALIZADA)
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
    
    # --- FUNÇÃO PARA CARREGAR E EXIBIR OS POSTS (LÓGICA DE FILTRO) ---
    def load_and_display_posts(search_term="", species_filter="", type_filter=""):
        posts_list.controls.clear()
        
        try:
            with session_scope() as s:
                # 4.1. Carregar todos os posts
                lost_animals = s.query(LostAnimal).all()
                found_reports = s.query(FoundReport).all()
                
                all_posts = []

                # Lógica de Filtro
                def passes_filter(post, is_lost):
                    # Filtro por tipo (Perdido/Encontrado)
                    current_type = "Perdido" if is_lost else "Encontrado"
                    if type_filter != "Qualquer" and type_filter != current_type: return False
                    
                    # Filtro por Espécie
                    post_species = post.species or ""
                    if species_filter.lower() != "qualquer" and post_species.lower() != species_filter.lower():
                        return False
                        
                    # Filtro por termo (Nome, Localização, Descrição)
                    if search_term:
                        term = search_term.lower()
                        # Campos relevantes para LostAnimal
                        if is_lost:
                            if term in (post.name or "").lower(): return True
                            if term in (post.lost_location or "").lower(): return True
                            if term in (post.desc_animal or "").lower(): return True
                        # Campos relevantes para FoundReport
                        else:
                            if term in (post.found_location or "").lower(): return True
                            if term in (post.found_description or "").lower(): return True
                        
                        return False # Se não passou em nenhum campo de busca
                        
                    return True # Passou nos filtros de Tipo e Espécie ou não tinha filtro de busca.


                # Processar posts de Animais Perdidos
                for a in lost_animals:
                    if passes_filter(a, is_lost=True):
                        card = build_post_card(
                            title=f"{a.name or 'Animal'} perdido", 
                            location_text=a.lost_location, 
                            description=a.desc_animal, 
                            lat=a.latitude, 
                            lon=a.longitude, 
                            is_lost=True, 
                            item_id=a.id,
                            on_edit_click=None, on_delete_click=None,
                            image_url=a.image_url # Passa a URL da imagem
                        )
                        all_posts.append(card)

                # Processar posts de Relatos Encontrados
                for r in found_reports:
                    if passes_filter(r, is_lost=False):
                        card = build_post_card(
                            title=f"{r.species or 'Animal'} encontrado", 
                            location_text=r.found_location, 
                            description=r.found_description, 
                            lat=r.latitude, 
                            lon=r.longitude, 
                            is_lost=False, 
                            item_id=r.id,
                            on_edit_click=None, on_delete_click=None,
                            image_url=r.image_url # Passa a URL da imagem
                        )
                        all_posts.append(card)
                    
                # Misturar e adicionar os posts (Ordenando por ID para aparecerem na ordem de criação)
                all_posts.sort(key=lambda x: x.content.content.controls[1].controls[3].value.split(': ')[1], reverse=True) # Assumindo que o ID é o 4º controle do Column

                posts_list.controls.extend(all_posts)

                if not all_posts:
                    posts_list.controls.append(ft.Text("Nenhum post disponível ou encontrado com os filtros aplicados."))

        except Exception as e:
            posts_list.controls.append(ft.Text(f"Erro ao carregar posts: {e}", color=ft.Colors.RED))
            print(f"Erro ao carregar posts na Home: {e}")
            
        page.update()

    # 2. Definição do cabeçalho com o botão de Logout
    header = ft.Row([
        ft.Text(f"Bem-vindo, {cur['username']}! (Feed de Posts)", size=24, weight=ft.FontWeight.BOLD),
        ft.ElevatedButton("Logout", on_click=do_logout_func, 
                          style=ft.ButtonStyle(bgcolor=ft.Colors.RED_400, color=ft.Colors.WHITE))
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    
    # 3. Definição dos botões de navegação
    navigation_buttons = ft.Row(
        [
            ft.ElevatedButton("Cadastrar Perdido", on_click=go_to_lost_reg_func),
            ft.ElevatedButton("Relatar Encontrado", on_click=go_to_found_reg_func),
            ft.ElevatedButton("Meus Posts", on_click=go_to_my_posts_func),
            ft.ElevatedButton("Ver Mapa", on_click=go_to_map_func),
        ],
        wrap=True,
        alignment=ft.MainAxisAlignment.START
    )

    # --- CAMPOS DE FILTRO (NOVO) ---
    search_field = ft.TextField(
        label="Buscar por nome, endereço ou descrição", 
        width=300, 
        on_submit=lambda e: load_and_display_posts(search_field.value, species_dropdown.value, type_dropdown.value)
    )
    
    species_options = [ft.dropdown.Option(s) for s in ["Qualquer", "Cachorro", "Gato", "Outro"]]
    species_dropdown = ft.Dropdown(
        label="Espécie",
        options=species_options,
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


    # 5. Adição dos controles à página
    page.add(
        header,
        ft.Divider(),
        navigation_buttons,
        ft.Divider(height=10),
        ft.Text("Filtros:", size=16, weight=ft.FontWeight.BOLD),
        search_controls, 
        ft.Divider(height=10),
        posts_list # Onde os posts serão exibidos
    )
    
    # Carrega os posts na primeira vez
    load_and_display_posts()
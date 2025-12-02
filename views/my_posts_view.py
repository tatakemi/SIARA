import flet as ft
from models import LostAnimal, FoundReport, session_scope 

# Tenta importar do serviço de geocoding (necessário para a imagem de mapa)
try:
    from services.geocoding import build_static_map_url
except ImportError:
    # Handler de fallback, se o serviço não for encontrado
    def build_static_map_url(*args, **kwargs):
        return "" 

# --- 1. Função Auxiliar para Construir o Card (Post Card) ---
# AGORA recebe os handlers de Edição e Exclusão como argumentos.
def build_post_card(title, location_text, description, lat, lon, is_lost, item_id, on_edit_click, on_delete_click):
    
    color = ft.Colors.RED_500 if is_lost else ft.Colors.GREEN_500
    
    # Imagem do Mapa Estático
    preview_image = ft.Image(src="", width=200, height=150)
    if lat is not None and lon is not None:
        preview_image.src = build_static_map_url(lat, lon, zoom=14, width=200, height=150)

    # Botões de Ação
    action_buttons = ft.Row([
        ft.ElevatedButton(
            "Editar", 
            icon=ft.Icons.EDIT, 
            on_click=on_edit_click,   # <-- Usa o handler injetado
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
        ),
        ft.ElevatedButton(
            "Excluir", 
            icon=ft.Icons.DELETE, 
            on_click=on_delete_click, # <-- Usa o handler injetado
            style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
        ),
    ])

    return ft.Card(
        elevation=4,
        content=ft.Container(
            padding=10,
            content=ft.Row([
                ft.Column(
                    [
                        ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=color),
                        ft.Text(f"Tipo: {'Perdido' if is_lost else 'Encontrado'}"),
                        ft.Text(f"Local: {location_text or 'Não informado'}"),
                        ft.Text(f"Descrição: {description or 'Sem descrição'}", max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        action_buttons
                    ],
                    expand=True,
                ),
                ft.Column([preview_image], horizontal_alignment=ft.CrossAxisAlignment.END)
            ],
            vertical_alignment=ft.CrossAxisAlignment.START)
        )
    )

# --- 2. Função Principal da View ---

# A assinatura AGORA tem 6 argumentos, incluindo os handlers de Edição/Exclusão.
def show_my_posts(page, state, go_to_home_func, create_edit_func, create_delete_func, show_snack_func):
    page.controls.clear()
    cur = state.get("current_user")
    if not cur:
        go_to_home_func() 
        return
        
    # --- Remova TODAS as funções aninhadas de show_edit_lost, delete_lost, etc. ---
    # A lógica de CRUD (exceto a exibição) está centralizada no app.py.

    my_lost_list = ft.Column()
    my_found_list = ft.Column()

    try:
        with session_scope() as s:
            # Carrega posts de animais perdidos
            lost_animals = s.query(LostAnimal).filter_by(owner_id=cur["id"]).order_by(LostAnimal.id.desc()).all()
            for a in lost_animals:
                # 3. Cria e injeta os handlers no card
                edit_handler = create_edit_func(item_id=a.id, is_lost=True)
                delete_handler = create_delete_func(item_id=a.id, is_lost=True)
                
                card = build_post_card(
                    title=a.name, 
                    location_text=a.lost_location, 
                    description=a.desc_animal, 
                    lat=a.latitude, 
                    lon=a.longitude, 
                    is_lost=True, 
                    item_id=a.id,
                    on_edit_click=edit_handler,     
                    on_delete_click=delete_handler  
                )
                my_lost_list.controls.append(card)

            # Carrega posts de animais encontrados
            found_reports = s.query(FoundReport).filter_by(finder_id=cur["id"]).order_by(FoundReport.id.desc()).all()
            for r in found_reports:
                # 3. Cria e injeta os handlers no card
                edit_handler = create_edit_func(item_id=r.id, is_lost=False)
                delete_handler = create_delete_func(item_id=r.id, is_lost=False)

                card = build_post_card(
                    title=r.species or "Animal encontrado", 
                    location_text=r.found_location, 
                    description=r.found_description, 
                    lat=r.latitude, 
                    lon=r.longitude, 
                    is_lost=False, 
                    item_id=r.id,
                    on_edit_click=edit_handler,     
                    on_delete_click=delete_handler  
                )
                my_found_list.controls.append(card)

    except Exception as e:
        show_snack_func(f"Erro ao carregar posts: {e}", is_error=True)

    header = ft.Container(
        content=ft.Row([
            ft.Text(f"Meus Posts: {cur['username']}", size=24, weight=ft.FontWeight.BOLD),
            ft.IconButton(icon=ft.Icons.HOME, on_click=go_to_home_func)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.only(bottom=10)
    )

    page.add(
        header, 
        ft.Text("Meus Registros de Animais Perdidos:", size=16, weight=ft.FontWeight.BOLD), 
        my_lost_list if my_lost_list.controls else ft.Text("Nenhum post de animal perdido encontrado."),
        ft.Divider(height=20),
        ft.Text("Meus Relatos de Animais Encontrados:", size=16, weight=ft.FontWeight.BOLD), 
        my_found_list if my_found_list.controls else ft.Text("Nenhum relato de animal encontrado."),
    )
    page.update()
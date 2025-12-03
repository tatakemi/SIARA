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
# AGORA recebe image_url como argumento.
def build_post_card(title, location_text, description, lat, lon, is_lost, item_id, on_edit_click, on_delete_click, image_url=None):
    
    color = ft.Colors.RED_500 if is_lost else ft.Colors.GREEN_500
    
    # Imagem do Animal (NOVO)
    # Prioriza a imagem do animal; se não houver, usa a imagem do mapa estático.
    if image_url:
        main_image = ft.Image(src=image_url, width=200, height=200, fit=ft.ImageFit.COVER)
        
    else:
        # Imagem do Mapa Estático (Lógica existente)
        preview_map_image = ft.Image(src="", width=200, height=200, fit=ft.ImageFit.COVER)
        if lat is not None and lon is not None:
            # Usa o marcador vermelho para perdido e verde para encontrado
            marker = "red-pushpin" if is_lost else "green-pushpin"
            preview_map_image.src = build_static_map_url(lat, lon, zoom=14, width=200, height=200, marker=marker)
        main_image = preview_map_image

    # Botões de Ação
    action_buttons = []
    if on_edit_click and on_delete_click:
        action_buttons = [
            ft.ElevatedButton(
                "Editar", 
                icon=ft.Icons.EDIT, 
                on_click=on_edit_click,   # <-- Usa o handler injetado
                data=(item_id, is_lost)
            ),
            ft.ElevatedButton(
                "Excluir", 
                icon=ft.Icons.DELETE, 
                on_click=on_delete_click, # <-- Usa o handler injetado
                data=(item_id, is_lost),
                style=ft.ButtonStyle(bgcolor=ft.Colors.RED_500, color=ft.Colors.WHITE)
            ),
        ]
    
    return ft.Card(
        content=ft.Container(
            padding=10,
            content=ft.Row([
                # 1. Imagem (Principal)
                main_image, 
                
                # 2. Informações
                ft.Column([
                    ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=color),
                    ft.Text(f"Local: {location_text or 'Não informado'}"),
                    ft.Text(f"Descrição: {description or 'Sem descrição.'}"),
                    ft.Text(f"ID: {item_id}", size=8, color=ft.Colors.BLACK54),
                    ft.Container(height=10),
                    ft.Row(action_buttons) 
                ], expand=True)
            ])
        )
    )


# --- 2. View Principal (show_my_posts) ---
def show_my_posts(page, state, go_to_home_func, create_edit_handler, create_delete_handler, show_snack_func):
    page.controls.clear()
    cur = state.get("current_user")
    if not cur:
        go_to_home_func()
        return

    my_lost_list = ft.ListView(expand=1, spacing=10, padding=20)
    my_found_list = ft.ListView(expand=1, spacing=10, padding=20)
    
    user_id = cur["id"]

    try:
        with session_scope() as s:
            
            # Carregar posts perdidos do usuário
            my_lost_animals = s.query(LostAnimal).filter_by(owner_id=user_id).all()
            for a in my_lost_animals:
                edit_handler = create_edit_handler(item_id=a.id, is_lost=True)
                delete_handler = create_delete_handler(item_id=a.id, is_lost=True)
                
                card = build_post_card(
                    title=f"{a.name or 'Animal'} perdido", 
                    location_text=a.lost_location, 
                    description=a.desc_animal, 
                    lat=a.latitude, 
                    lon=a.longitude, 
                    is_lost=True, 
                    item_id=a.id,
                    on_edit_click=edit_handler,     
                    on_delete_click=delete_handler,
                    image_url=a.image_url # NOVO: Passando a URL da imagem
                )
                my_lost_list.controls.append(card)

            # Carregar posts encontrados do usuário
            my_found_reports = s.query(FoundReport).filter_by(finder_id=user_id).all()
            for r in my_found_reports:
                edit_handler = create_edit_handler(item_id=r.id, is_lost=False)
                delete_handler = create_delete_handler(item_id=r.id, is_lost=False)

                card = build_post_card(
                    title=f"{r.species or 'Animal'} encontrado", 
                    location_text=r.found_location, 
                    description=r.found_description, 
                    lat=r.latitude, 
                    lon=r.longitude, 
                    is_lost=False, 
                    item_id=r.id,
                    on_edit_click=edit_handler,     
                    on_delete_click=delete_handler,
                    image_url=r.image_url # NOVO: Passando a URL da imagem
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
        my_lost_list if my_lost_list.controls else ft.Text("Nenhum registro de animal perdido."),
        ft.Divider(),
        ft.Text("Meus Relatos de Animais Encontrados:", size=16, weight=ft.FontWeight.BOLD), 
        my_found_list if my_found_list.controls else ft.Text("Nenhum relato de animal encontrado.")
    )
    page.update()
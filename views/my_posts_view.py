# my_posts_view.py
import flet as ft
from models import LostAnimal, FoundReport, session_scope 

# Tenta importar do serviço de geocoding (necessário para a imagem de mapa)
try:
    # Assumindo que este serviço existe
    from services.geocoding import build_static_map_url
except ImportError:
    # Handler de fallback, se o serviço não for encontrado
    def build_static_map_url(*args, **kwargs):
        return "" 

# --- 1. Função Auxiliar para Construir o Card (Post Card) ---
def build_post_card(title, location_text, description, lat, lon, is_lost, item_id, on_edit_click, on_delete_click):
    
    color = ft.Colors.RED_500 if is_lost else ft.Colors.GREEN_500
    
    # Imagem do Mapa Estático
    preview_image = ft.Image(src="", width=200, height=150)
    if lat is not None and lon is not None:
        try:
            preview_image.src = build_static_map_url(lat, lon, zoom=14, width=200, height=150)
        except Exception:
            pass # Ignora se a função não estiver pronta

    # Botões de Ação
    action_buttons = ft.Row(controls=[])
    
    # Adiciona botão de editar APENAS se o handler for fornecido (não é fornecido na Home)
    if on_edit_click:
        action_buttons.controls.append(
            ft.ElevatedButton(
                "Editar", 
                icon=ft.Icons.EDIT, 
                on_click=on_edit_click,
                style=ft.ButtonStyle(bgcolor=ft.Colors.AMBER_700, color=ft.Colors.BLACK)
            )
        )
        
    # Adiciona botão de excluir APENAS se o handler for fornecido (não é fornecido na Home)
    if on_delete_click:
        action_buttons.controls.append(
            ft.ElevatedButton(
                "Excluir", 
                icon=ft.Icons.DELETE_FOREVER, 
                on_click=on_delete_click,
                style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
            )
        )

    return ft.Card(
        elevation=4,
        content=ft.Container(
            padding=10,
            content=ft.Column(
                [
                    ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=color),
                    ft.Divider(height=5),
                    ft.Row([
                        ft.Column(
                            [
                                ft.Text(f"Local: {location_text or 'Não informado'}"),
                                ft.Text(f"Descrição: {description or 'N/A'}"),
                            ],
                            expand=True
                        ),
                        ft.Container(preview_image, border_radius=5)
                    ],
                    alignment=ft.MainAxisAlignment.START),
                    action_buttons
                ]
            )
        )
    )

# --- 2. View Principal ---
def show_my_posts(page, state, go_to_home_func, create_edit_func, create_delete_func, show_snack_func):
    page.controls.clear()
    cur = state.get("current_user")
    if not cur:
        go_to_home_func()
        return

    my_lost_list = ft.Column(spacing=10, scroll=ft.ScrollMode.ALWAYS, height=250)
    my_found_list = ft.Column(spacing=10, scroll=ft.ScrollMode.ALWAYS, height=250)

    try:
        with session_scope() as s:
            lost_animals = s.query(LostAnimal).filter_by(owner_id=cur["id"]).order_by(LostAnimal.id.desc()).all()
            found_reports = s.query(FoundReport).filter_by(finder_id=cur["id"]).order_by(FoundReport.id.desc()).all()

            for a in lost_animals:
                edit_handler = create_edit_func(item_id=a.id, is_lost=True)
                delete_handler = create_delete_func(item_id=a.id, is_lost=True)
                
                card = build_post_card(
                    title=f"Perdido: {a.name or 'Sem nome'}", 
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

            for r in found_reports:
                edit_handler = create_edit_func(item_id=r.id, is_lost=False)
                delete_handler = create_delete_func(item_id=r.id, is_lost=False)

                card = build_post_card(
                    title=f"Encontrado: {r.species or 'Animal'}", 
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
        my_lost_list if my_lost_list.controls else ft.Text("Nenhum registro de animal perdido encontrado.", italic=True),
        ft.Divider(),
        ft.Text("Meus Relatos de Animais Encontrados:", size=16, weight=ft.FontWeight.BOLD),
        my_found_list if my_found_list.controls else ft.Text("Nenhum relato de animal encontrado.", italic=True)
    )
    page.update()
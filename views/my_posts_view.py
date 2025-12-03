import flet as ft
from models import LostAnimal, FoundReport, session_scope 
from functools import partial
from urllib.parse import quote # <-- CORREÇÃO: Usando a função de URL encode padrão do Python

# Tenta importar do serviço de geocoding (necessário para a imagem de mapa)
try:
    from services.geocoding import build_static_map_url
except ImportError:
    # Handler de fallback, se o serviço não for encontrado
    def build_static_map_url(*args, **kwargs):
        return "" 

# --- 1. Função Auxiliar para Construir o Card (Post Card) ---
def build_post_card(page: ft.Page, title, location_text, description, lat, lon, is_lost, item_id, on_edit_click, on_delete_click, image_url=None):
    
    color = ft.Colors.RED_500 if is_lost else ft.Colors.GREEN_500
    emoji = "🐾" if is_lost else "🏠"

    # ------------------ LÓGICA DE COMPARTILHAMENTO ------------------
    share_text = f"🚨 URGENTE: {'ANIMAL PERDIDO' if is_lost else 'ANIMAL ENCONTRADO'}! {title} em {location_text}. Descrição: {description or 'Detalhes no link.'}. Ajude a compartilhar!"
    
    base_url = "https://www.google.com/search?q=ajuda+animal+perdido" 
    if lat is not None and lon is not None:
         base_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    
    
    # 1. Compartilhar no Facebook (USANDO quote)
    facebook_share_link = f"https://www.facebook.com/sharer/sharer.php?u={quote(base_url)}&quote={quote(share_text)}"
    
    # 2. Compartilhar no WhatsApp (USANDO quote)
    whatsapp_share_link = f"https://wa.me/?text={quote(share_text)}%20{quote(base_url)}"
    
    share_buttons = ft.Row([
        ft.Text("Compartilhar:", size=10, weight=ft.FontWeight.BOLD),
        ft.IconButton(
            ft.Icons.SHARE,  # <-- CORREÇÃO: Usando ícone genérico de SHARE
            icon_color=ft.Colors.BLUE_900, 
            tooltip="Compartilhar no Facebook",
            on_click=lambda e: page.launch_url(facebook_share_link)
        ),
        ft.IconButton(
            ft.Icons.MESSAGE,  # <-- CORREÇÃO: Usando ícone genérico de MESSAGE (ou SHARE)
            icon_color=ft.Colors.GREEN_700, 
            tooltip="Compartilhar no WhatsApp",
            on_click=lambda e: page.launch_url(whatsapp_share_link)
        )
    ], alignment=ft.MainAxisAlignment.END)
    # ------------------ FIM: LÓGICA DE COMPARTILHAMENTO ------------------

    # Imagem do Animal
    if image_url:
        main_image = ft.Image(src=image_url, width=200, height=200, fit=ft.ImageFit.COVER, border_radius=ft.border_radius.all(5))
        
    else:
        # Imagem do Mapa Estático (Fallback)
        preview_map_image = ft.Image(src="", width=200, height=200, fit=ft.ImageFit.COVER)
        if lat is not None and lon is not None:
            preview_map_image.src = build_static_map_url(lat, lon, zoom=14, width=200, height=200)
        
        main_image = preview_map_image

    # Botões de Ação para Edição e Exclusão
    action_buttons = []
    if on_edit_click and on_delete_click:
        action_buttons = [
            ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.BLUE_ACCENT_400, on_click=on_edit_click, tooltip="Editar Post"), 
            ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_ACCENT_400, on_click=on_delete_click, tooltip="Excluir Post") 
        ]

    return ft.Card(
        ft.Container(
            padding=10,
            content=ft.Column([
                ft.Row([
                    ft.Text(f"{emoji} {'PERDIDO' if is_lost else 'ENCONTRADO'} - {title}", 
                            weight=ft.FontWeight.BOLD, color=color, size=16),
                    main_image
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Text(f"ID: {item_id}", size=10), 
                ft.Text(f"Local: {location_text or 'Não informado'}"),
                ft.Text(f"Descrição: {description or 'Nenhuma descrição.'}", size=12, italic=True, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Divider(height=1),
                ft.Row(
                    [
                        ft.Row(action_buttons, alignment=ft.MainAxisAlignment.START),
                        ft.VerticalDivider(width=1) if action_buttons else ft.Container(),
                        share_buttons 
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
            ])
        ),
        width=400
    )


def show_my_posts(page, state, go_to_home_func, create_edit_handler_func, create_delete_handler_func, show_snack_func):
    page.controls.clear()
    cur = state.get("current_user")
    
    if not cur:
        go_to_home_func() 
        return

    my_lost_list = ft.ListView(expand=1, spacing=10, padding=20)
    my_found_list = ft.ListView(expand=1, spacing=10, padding=20)

    try:
        with session_scope() as s:
            # 1. Posts de Animais Perdidos
            lost_animals = s.query(LostAnimal).filter_by(owner_id=cur["id"]).all()
            for a in lost_animals:
                # Handlers com o ID e tipo de post fixados (partial)
                edit_handler = partial(create_edit_handler_func, item_id=a.id, is_lost=True)
                delete_handler = partial(create_delete_handler_func, item_id=a.id, is_lost=True)
                
                # Certifique-se de passar 'page' para build_post_card
                card = build_post_card(
                    page, 
                    title=a.name or "Animal perdido", 
                    location_text=a.lost_location, 
                    description=a.desc_animal, 
                    lat=a.latitude, 
                    lon=a.longitude, 
                    is_lost=True, 
                    item_id=a.id,
                    on_edit_click=edit_handler,     
                    on_delete_click=delete_handler,
                    image_url=a.image_url 
                )
                my_lost_list.controls.append(card)

            # 2. Relatos de Animais Encontrados
            found_reports = s.query(FoundReport).filter_by(finder_id=cur["id"]).all()
            for r in found_reports:
                # Handlers com o ID e tipo de post fixados (partial)
                edit_handler = partial(create_edit_handler_func, item_id=r.id, is_lost=False)
                delete_handler = partial(create_delete_handler_func, item_id=r.id, is_lost=False)

                # Certifique-se de passar 'page' para build_post_card
                card = build_post_card(
                    page, 
                    title=f"{r.species or 'Animal'} encontrado", 
                    location_text=r.found_location, 
                    description=r.found_description, 
                    lat=r.latitude, 
                    lon=r.longitude, 
                    is_lost=False, 
                    item_id=r.id,
                    on_edit_click=edit_handler,     
                    on_delete_click=delete_handler,
                    image_url=r.image_url 
                )
                my_found_list.controls.append(card)

    except Exception as e:
        show_snack_func(f"Erro ao carregar posts: {e}", is_error=True)
        print(f"Erro ao carregar posts em my_posts_view: {e}")

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
        my_lost_list if my_lost_list.controls else ft.Text("Nenhum animal perdido registrado por você."),
        ft.Divider(),
        ft.Text("Meus Relatos de Animais Encontrados:", size=16, weight=ft.FontWeight.BOLD), 
        my_found_list if my_found_list.controls else ft.Text("Nenhum relato de animal encontrado por você."),
        ft.Divider(),
        ft.ElevatedButton("Voltar para Home", on_click=go_to_home_func)
    )
    page.update()
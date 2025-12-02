import flet as ft
from models import LostAnimal, FoundReport, session_scope #

def my_posts_view(page, state, go_to_home_func, show_snack_func):
    page.controls.clear()
    cur = state.get("current_user")
    if not cur:
        go_to_home_func() 
        return
        
    # --- Funções de Edição e Deleção (aninhadas ou definidas fora) ---
    def show_edit_lost(animal_id):
        show_snack_func(f"Funcionalidade de Edição (Lost ID: {animal_id}) - Não implementada", success=False)
        page.update() 
    
    def show_edit_found(report_id):
        show_snack_func(f"Funcionalidade de Edição (Found ID: {report_id}) - Não implementada", success=False)
        page.update()

    def delete_lost(e, animal_id):
        with session_scope() as s: #
            animal = s.query(LostAnimal).filter_by(id=animal_id, owner_id=cur["id"]).first() #
            if animal:
                s.delete(animal)
                show_snack_func("Post perdido excluído com sucesso.")
            else:
                show_snack_func("Erro: Post não encontrado ou você não é o dono.", success=False)
        my_posts_view(page, state, go_to_home_func, show_snack_func) # Recarrega a view

    def delete_found(e, report_id):
        with session_scope() as s: #
            report = s.query(FoundReport).filter_by(id=report_id, finder_id=cur["id"]).first() #
            if report:
                s.delete(report)
                show_snack_func("Post encontrado excluído com sucesso.")
            else:
                show_snack_func("Erro: Post não encontrado ou você não é o dono.", success=False)
        my_posts_view(page, state, go_to_home_func, show_snack_func) # Recarrega a view

    # --- Componente para formatar um único post ---
    def build_post_card(title, location_text, description, lat, lon, is_lost, item_id):
        location_coords = ""
        if lat is not None and lon is not None:
            location_coords = f"Coordenadas: {lat:.6f}, {lon:.6f}"
        
        actions = ft.Row([
            ft.IconButton(ft.icons.EDIT, on_click=lambda e: (show_edit_lost(item_id) if is_lost else show_edit_found(item_id)), tooltip="Editar"),
            # Passa o ID do item para a função de deleção
            ft.IconButton(ft.icons.DELETE, on_click=lambda e: (delete_lost(e, item_id) if is_lost else delete_found(e, item_id)), tooltip="Deletar", icon_color=ft.Colors.RED_700),
        ], alignment=ft.MainAxisAlignment.END)

        card_color = ft.Colors.INDIGO_ACCENT if is_lost else ft.Colors.GREEN_100
        status_text = "Animal Perdido" if is_lost else "Animal Encontrado"
        
        return ft.Card(
            content=ft.Container(
                bgcolor=card_color,
                padding=15,
                border_radius=10,
                content=ft.Column([
                    ft.Row([
                        ft.Text(f"📌 {status_text}", weight=ft.FontWeight.BOLD),
                        actions
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=5, color=ft.Colors.BLACK12),
                    ft.Text(f"Localização: {location_text or 'Não informado'}"),
                    ft.Text(location_coords, size=12, italic=True),
                    ft.Text(f"Descrição: {description or 'N/A'}", max_lines=3, overflow=ft.TextOverflow.ELLIPSIS),
                ])
            ),
            elevation=4,
        )

    # --- Carregando e exibindo os Posts ---

    my_lost_list = ft.ListView(expand=True, spacing=15)
    my_found_list = ft.ListView(expand=True, spacing=15)

    with session_scope() as s: #
        # Carrega posts de animais perdidos
        lost_animals = s.query(LostAnimal).filter_by(owner_id=cur["id"]).order_by(LostAnimal.id.desc()).all() #
        for a in lost_animals:
            card = build_post_card(title=a.name, location_text=a.lost_location, description=a.desc_animal, lat=a.latitude, lon=a.longitude, is_lost=True, item_id=a.id)
            my_lost_list.controls.append(card)

        # Carrega posts de animais encontrados
        found_reports = s.query(FoundReport).filter_by(finder_id=cur["id"]).order_by(FoundReport.id.desc()).all() #
        for r in found_reports:
            card = build_post_card(title=r.species or "Animal encontrado", location_text=r.found_location, description=r.found_description, lat=r.latitude, lon=r.longitude, is_lost=False, item_id=r.id)
            my_found_list.controls.append(card)

    page.add(
        ft.Text(f"Meus Posts: {cur['username']}", size=18),
        ft.Row([ft.ElevatedButton("Voltar para Home", on_click=go_to_home_func)]),
        ft.Text("Meus Registros de Animais Perdidos:", size=16, weight=ft.FontWeight.BOLD), 
        my_lost_list if my_lost_list.controls else ft.Text("Nenhum post de animal perdido encontrado."),
        ft.Divider(height=20),
        ft.Text("Meus Relatos de Animais Encontrados:", size=16, weight=ft.FontWeight.BOLD), 
        my_found_list if my_found_list.controls else ft.Text("Nenhum relato de animal encontrado."),
    )
    page.update()

show_my_posts = my_posts_view
import flet as ft
from models import LostAnimal, FoundReport, session_scope #

def do_logout(state, go_to_login_func):
    state["current_user"] = None
    go_to_login_func()

def home_view(page, state, go_to_login_func, go_to_lost_reg_func, go_to_found_reg_func, go_to_my_posts_func, go_to_map_func):
    page.controls.clear()
    cur = state.get("current_user")
    
    if not cur:
        go_to_login_func() 
        return
        
    logout_func = lambda e: do_logout(state, go_to_login_func)

    header = ft.Text(f"Bem-vindo(a), {cur['username']}", size=18)
    btn_lost = ft.ElevatedButton("Registrar animal perdido", on_click=go_to_lost_reg_func)
    btn_found = ft.ElevatedButton("Registrar animal encontrado", on_click=go_to_found_reg_func)
    btn_my = ft.ElevatedButton("Meus posts", on_click=go_to_my_posts_func)
    btn_map = ft.ElevatedButton("Abrir mapa (browser)", on_click=go_to_map_func)
    btn_logout = ft.TextButton("Sair", on_click=logout_func)

    lost_list = ft.ListView(expand=True, spacing=10)
    found_list = ft.ListView(expand=True, spacing=10)

    with session_scope() as s: #
        # Carrega dados do DB
        for a in s.query(LostAnimal).order_by(LostAnimal.id.desc()).all(): #
            owner_name = a.owner.username if a.owner else "—"
            info = f"Tutor: {owner_name}\nOnde foi perdido: {a.lost_location or ''}\nDescrição: {a.desc_animal or ''}"
            if a.latitude and a.longitude:
                info += f"\nCoordenadas: {a.latitude:.6f}, {a.longitude:.6f}"
            lost_list.controls.append(ft.Container(ft.ListTile(title=ft.Text(a.name), subtitle=ft.Text(info)), bgcolor=ft.Colors.BLACK12, padding=12, margin=3, border_radius=8))
        
        for r in s.query(FoundReport).order_by(FoundReport.id.desc()).all(): #
            finder_name = r.finder.username if r.finder else "—"
            info = f"Quem encontrou: {finder_name}\nOnde foi encontrado: {r.found_location or ''}\nDescrição: {r.found_description or ''}"
            if r.latitude and r.longitude:
                info += f"\nCoordenadas: {r.latitude:.6f}, {r.longitude:.6f}"
            found_list.controls.append(ft.Container(ft.ListTile(title=ft.Text(r.species or "Animal encontrado"), subtitle=ft.Text(info)), bgcolor=ft.Colors.INDIGO_ACCENT, padding=12, margin=3, border_radius=8))

    page.add(header, ft.Row([btn_lost, btn_found, btn_my, btn_map, btn_logout]), ft.Text("Animais perdidos (Feed):"), lost_list, ft.Text("Animais encontrados (Feed):"), found_list)
    page.update()

show_home = home_view
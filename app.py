# app.py (Router Central Limpo - Prontp para Usar)
import flet as ft
import webbrowser

# Importa a lógica de banco de dados
from models import User, LostAnimal, FoundReport, session_scope, session

# ************************************************************
# IMPORTAÇÃO DOS SERVIÇOS MODULARIZADOS
# ************************************************************
# Importa o Geocoding
from services.geocoding import (
    geocode_address, reverse_geocode, build_static_map_url
)
# Importa o Servidor do Mapa
from services.map_server import (
    find_free_port, start_map_server, stop_map_server, 
    write_base_map_html, LAST_PICK
)
# ************************************************************


def main(page: ft.Page):
    # ---- 1. Configuração da Página e Estado ----
    page.title = "SIARA"
    page.window_width = 1000
    page.window_height = 700
    page.padding = 20

    state = {"current_user": None, "map_port": None}

    # ---- 2. Inicialização dos Serviços (Usando funções importadas) ----
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
    
    # ---- 3. Utilitários de Feedback (show_snack) ----
    def show_snack(message: str, success: bool = True):
        color = ft.Colors.GREEN if success else ft.Colors.RED
        page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    # *******************************************************************
    # 4. FUNÇÕES DE UI (PASTE DA SUA LÓGICA ORIGINAL)
    # 
    # Mantenha aqui TODAS as suas funções de interface de usuário (UI):
    # show_login, show_register, show_home, do_logout, show_my_posts,
    # show_lost_registration, show_found_registration, show_map, 
    # e todas as suas funções de edição/deleção.
    # 
    # Estas funções JÁ estão usando as variáveis e funções importadas
    # (como geocode_address, LAST_PICK, build_static_map_url).
    # *******************************************************************

    # Cole o código da sua função show_login (e todas as dependentes) aqui:
    def show_login(e=None):
        page.controls.clear()
        username = ft.TextField(label="Usuário")
        password = ft.TextField(label="Senha", password=True, can_reveal_password=True)
        msg = ft.Text("", color=ft.Colors.RED)

        def do_login(ev):
            uname = username.value.strip()
            pwd = password.value or ""
            if not uname:
                msg.value = "Insira o nome de usuário"
                page.update()
                return
            with session_scope() as s:
                user = s.query(User).filter_by(username=uname).first()
                if user and user.check_password(pwd):
                    state["current_user"] = {"id": user.id, "username": user.username}
                    show_home()
                else:
                    msg.value = "Usuário ou senha inválidos"
                    page.update()

        page.add(ft.Text("Login", size=20), username, password,
                 ft.Row([ft.ElevatedButton("Log-in", on_click=do_login),
                         ft.TextButton("Não tenho uma conta", on_click=show_register)]), msg)

    # Cole o código da sua função show_register (e todas as dependentes) aqui:
    def show_register(e=None):
        page.controls.clear()
        username = ft.TextField(label="Usuário")
        contact = ft.TextField(label="Contato (telefone/email)")
        password = ft.TextField(label="Senha", password=True, can_reveal_password=True)
        password2 = ft.TextField(label="Confirmar senha", password=True, can_reveal_password=True)
        msg = ft.Text("", color=ft.Colors.RED)

        def do_register(ev):
            uname = username.value.strip()
            pwd = password.value or ""
            pwd2 = password2.value or ""
            if pwd != pwd2 or not pwd:
                msg.value = "As senhas não coincidem ou estão vazias"
                page.update()
                return
            with session_scope() as s:
                existing = s.query(User).filter_by(username=uname).first()
                if existing:
                    msg.value = "Usuário já existe"
                    page.update()
                    return
                u = User(username=uname, contact=contact.value.strip())
                u.set_password(pwd)
                s.add(u)
                s.flush()
                state["current_user"] = {"id": u.id, "username": u.username}
            show_snack("Account created; you are now logged in.")
            show_home()
            
        page.add(ft.Text("Registro", size=20), username, contact, password, password2,
                 ft.Row([ft.ElevatedButton("Registrar", on_click=do_register),
                         ft.TextButton("Voltar para Login", on_click=show_login)]), msg)

    # Cole o código da sua função do_logout aqui:
    def do_logout(e):
        state["current_user"] = None
        show_login()

    # Cole o código da sua função show_home (e todas as dependentes) aqui:
    def show_home(e=None):
        page.controls.clear()
        cur = state["current_user"]
        if not cur:
            show_login()
            return
        header = ft.Text(f"Welcome, {cur['username']}", size=18)
        btn_lost = ft.ElevatedButton("Registrar animal perdido", on_click=show_lost_registration)
        btn_found = ft.ElevatedButton("Registrar animal encontrado", on_click=show_found_registration)
        # Note: show_my_posts, show_edit_lost, show_edit_found devem ser coladas abaixo
        btn_my = ft.ElevatedButton("Meus posts", on_click=show_my_posts)
        btn_map = ft.ElevatedButton("Abrir mapa (browser)", on_click=show_map)
        btn_logout = ft.TextButton("Sair", on_click=do_logout)

        lost_list = ft.ListView(expand=True, spacing=10)
        found_list = ft.ListView(expand=True, spacing=10)

        with session_scope() as s:
            for a in s.query(LostAnimal).order_by(LostAnimal.id.desc()).all():
                owner_name = a.owner.username if a.owner else "—"
                info = f"Tutor: {owner_name}\nOnde foi perdido: {a.lost_location or ''}\nDescrição: {a.desc_animal or ''}"
                if a.latitude and a.longitude:
                    info += f"\nCoordenadas: {a.latitude:.6f}, {a.longitude:.6f}"
                lost_list.controls.append(ft.Container(ft.ListTile(title=ft.Text(a.name), subtitle=ft.Text(info)), bgcolor=ft.Colors.BLACK12, padding=12, margin=3, border_radius=8))
            for r in s.query(FoundReport).order_by(FoundReport.id.desc()).all():
                finder_name = r.finder.username if r.finder else "—"
                info = f"Quem encontrou: {finder_name}\nOnde foi encontrado: {r.found_location or ''}\nDescrição: {r.found_description or ''}"
                if r.latitude and r.longitude:
                    info += f"\nCoordenadas: {r.latitude:.6f}, {r.longitude:.6f}"
                found_list.controls.append(ft.Container(ft.ListTile(title=ft.Text(r.species or "Animal encontrado"), subtitle=ft.Text(info)), bgcolor=ft.Colors.INDIGO_ACCENT, padding=12, margin=3, border_radius=8))

        page.add(header, ft.Row([btn_lost, btn_found, btn_my, btn_map, btn_logout]), ft.Text("Animais perdidos:"), lost_list, ft.Text("Animais encontrados:"), found_list)

    # Cole o código da sua função show_lost_registration aqui (e dependentes):
    def show_lost_registration(e=None):
        page.controls.clear()
        cur = state["current_user"]
        if not cur:
            show_login()
            return
        name = ft.TextField(label="Nome do animal")
        species = ft.TextField(label="Espécie (opcional)")
        location = ft.TextField(label="Onde foi perdido (endereço ou descrição)")
        desc = ft.TextField(label="Descrição do animal (opcional)")
        contact = ft.TextField(label="Contato (opcional)")
        lat_field = ft.TextField(label="Latitude (opcional)")
        lon_field = ft.TextField(label="Longitude (opcional)")
        msg = ft.Text("")

        preview_image = ft.Image(src="", width=600, height=300)
        preview_address = ft.Text("", selectable=True)

        def update_preview_from_fields():
            try:
                if lat_field.value.strip() and lon_field.value.strip():
                    lat = float(lat_field.value.strip()); lon = float(lon_field.value.strip())
                    preview_image.src = build_static_map_url(lat, lon)
                    preview_address.value = reverse_geocode(lat, lon) or "No address found for these coordinates."
                else:
                    preview_image.src = ""
                    preview_address.value = ""
            except Exception:
                preview_image.src = ""
                preview_address.value = ""
            try:
                preview_image.update()
            except:
                pass
            try:
                preview_address.update()
            except:
                pass
            page.update()

        def do_register_lost(ev):
            if not name.value.strip():
                msg.value = "Nome é obrigatório"
                page.update()
                return
            lat = None; lon = None
            if lat_field.value.strip() and lon_field.value.strip():
                try:
                    lat = float(lat_field.value.strip())
                    lon = float(lon_field.value.strip())
                except:
                    msg.value = "Formato de coordenadas inválido"
                    page.update()
                    return
            else:
                lat, lon = geocode_address(location.value.strip())

            with session_scope() as s:
                la = LostAnimal(
                    name=name.value.strip(),
                    species=species.value.strip() or None,
                    lost_location=location.value.strip() or None,
                    desc_animal=desc.value.strip() or None,
                    contact=contact.value.strip() or None,
                    owner_id=cur["id"],
                    latitude=lat,
                    longitude=lon
                )
                s.add(la)
            show_snack("Animal perdido registrado.")
            name.value = species.value = location.value = desc.value = contact.value = ""
            lat_field.value = lon_field.value = ""
            update_preview_from_fields()
            page.update()

        def fetch_picked_coords(ev):
            lat = LAST_PICK.get("lat")
            lon = LAST_PICK.get("lon")
            if lat is None or lon is None:
                msg.value = "Coordenadas não selecionadas ainda — clique no mapa primeiro."
            else:
                lat_field.value = f"{lat:.6f}"
                lon_field.value = f"{lon:.6f}"
                msg.value = "Coordenadas importadas para o formulário."
                update_preview_from_fields()
            page.update()
            
        page.add(ft.Text("Register Lost Animal", size=18),
                 name, species, location, desc, contact,
                 ft.Row([lat_field, lon_field]),
                 ft.Row([ft.ElevatedButton("Atualizar coordenadas selecionadas", on_click=fetch_picked_coords),
                         ft.ElevatedButton("Atualizar mapa", on_click=lambda e: (update_preview_from_fields())),
                         ft.ElevatedButton("Salvar", on_click=do_register_lost),
                         ft.TextButton("Voltar", on_click=show_home)]),
                 preview_image,
                 preview_address,
                 msg)
    
    # Cole o código da sua função show_found_registration aqui (e dependentes):
    def show_found_registration(e=None):
        page.controls.clear()
        cur = state["current_user"]
        if not cur:
            show_login()
            return
        species = ft.TextField(label="Espécie (opcional)")
        location = ft.TextField(label="Onde foi encontrado (endereço ou descrição)")
        date = ft.TextField(label="Data (opcional)")
        desc = ft.TextField(label="Descrição do animal")
        lat_field = ft.TextField(label="Latitude (opcional)")
        lon_field = ft.TextField(label="Longitude (opcional)")
        msg = ft.Text("")

        preview_image = ft.Image(src="", width=600, height=300)
        preview_address = ft.Text("", selectable=True)

        def update_preview_from_fields():
            try:
                if lat_field.value.strip() and lon_field.value.strip():
                    lat = float(lat_field.value.strip()); lon = float(lon_field.value.strip())
                    preview_image.src = build_static_map_url(lat, lon)
                    preview_address.value = reverse_geocode(lat, lon) or "No address found for these coordinates."
                else:
                    preview_image.src = ""
                    preview_address.value = ""
            except Exception:
                preview_image.src = ""
                preview_address.value = ""
            try:
                preview_image.update()
            except:
                pass
            try:
                preview_address.update()
            except:
                pass
            page.update()

        def do_register_found(ev):
            lat = None; lon = None
            if lat_field.value.strip() and lon_field.value.strip():
                try:
                    lat = float(lat_field.value.strip())
                    lon = float(lon_field.value.strip())
                except:
                    msg.value = "Formato de coordenadas inválido"
                    page.update()
                    return
            else:
                lat, lon = geocode_address(location.value.strip())

            with session_scope() as s:
                fr = FoundReport(
                    species=species.value.strip() or None,
                    found_location=location.value.strip() or None,
                    found_date=date.value.strip() or None,
                    found_description=desc.value.strip() or None,
                    finder_id=cur["id"],
                    latitude=lat,
                    longitude=lon
                )
                s.add(fr)
            show_snack("Registro de animal encontrado salvo.")
            species.value = location.value = date.value = desc.value = ""
            lat_field.value = lon_field.value = ""
            update_preview_from_fields()
            page.update()

        def fetch_picked_coords(ev):
            lat = LAST_PICK.get("lat")
            lon = LAST_PICK.get("lon")
            if lat is None or lon is None:
                msg.value = "Coordenadas não selecionadas ainda — clique no mapa primeiro."
            else:
                lat_field.value = f"{lat:.6f}"
                lon_field.value = f"{lon:.6f}"
                msg.value = "Coordenadas importadas para o formulário."
                update_preview_from_fields()
            page.update()

        page.add(ft.Text("Registrar animal encontrado", size=18),
                 species, location, date, desc,
                 ft.Row([lat_field, lon_field]),
                 ft.Row([ft.ElevatedButton("Atualizar coordenadas selecionadas", on_click=fetch_picked_coords),
                         ft.ElevatedButton("Atualizar mapa", on_click=lambda e: (update_preview_from_fields())),
                         ft.ElevatedButton("Salvar", on_click=do_register_found),
                         ft.TextButton("Voltar", on_click=show_home)]),
                 preview_image,
                 preview_address,
                 msg)

    # Cole o código da sua função show_map (e todas as dependentes) aqui:
    def show_map(e=None):
        port = state["map_port"]
        map_url = f"http://127.0.0.1:{port}/map.html"
        try:
            webbrowser.open(map_url)
        except Exception as ex:
            print("Failed to open browser:", ex)
        page.controls.clear()
        page.add(ft.Text("Mapa aberto no seu navegador", size=18),
                 ft.Text("Clique no mapa, retorne ao app e então lique em 'atualizar coordenadas'", selectable=True),
                 ft.Row([ft.ElevatedButton("Voltar", on_click=show_home),
                         ft.ElevatedButton("Abrir mapa no navegador", on_click=lambda e: webbrowser.open(map_url))]),
                 ft.Text(f"Map URL: {map_url}", selectable=True))


    # Cole o código da sua função show_my_posts e todas as funções de edição/deleção aqui:
    # (Não tenho esse código completo, então você deve colá-lo)
    def show_my_posts(e=None):
        show_snack("Implemente a função show_my_posts para ver a lista de posts do usuário.")
        show_home() # Placeholder
    # ... cole todas as outras funções de UI que faltam aqui (se existirem) ...


    # ---- 5. Início da UI ----
    show_login()

if __name__ == "__main__":
    ft.app(target=main)
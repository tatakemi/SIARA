import flet as ft
from models import LostAnimal, session_scope #
from services.geocoding import geocode_address, reverse_geocode, build_static_map_url #
from services.map_server import LAST_PICK #

def lost_registration_view(page, state, go_to_home_func, show_snack_func):
    page.controls.clear()
    cur = state.get("current_user")
    if not cur:
        go_to_home_func()
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
        # Lógica de atualização do mapa estático
        try:
            if lat_field.value.strip() and lon_field.value.strip():
                lat = float(lat_field.value.strip()); lon = float(lon_field.value.strip())
                preview_image.src = build_static_map_url(lat, lon) #
                preview_address.value = reverse_geocode(lat, lon) or "Endereço não encontrado para estas coordenadas." #
            else:
                preview_image.src = ""
                preview_address.value = ""
        except Exception:
            preview_image.src = ""
            preview_address.value = ""
            msg.value = "Erro ao atualizar o mapa. Verifique as coordenadas."
        
        page.update()

    def do_register_lost(ev):
        # Lógica de registro e geocodificação
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
        elif location.value.strip():
            lat, lon = geocode_address(location.value.strip()) #

        with session_scope() as s: #
            la = LostAnimal(
                name=name.value.strip(), species=species.value.strip() or None,
                lost_location=location.value.strip() or None, desc_animal=desc.value.strip() or None,
                contact=contact.value.strip() or None, owner_id=cur["id"], latitude=lat, longitude=lon
            ) #
            s.add(la)
        
        show_snack_func("Animal perdido registrado.")
        # Limpar campos e recarregar preview
        name.value = species.value = location.value = desc.value = contact.value = ""
        lat_field.value = lon_field.value = ""
        update_preview_from_fields()
        
    def fetch_picked_coords(ev):
        # Lógica para pegar as últimas coordenadas clicadas no mapa
        lat = LAST_PICK.get("lat") #
        lon = LAST_PICK.get("lon") #
        if lat is None or lon is None:
            msg.value = "Coordenadas não selecionadas ainda — clique no mapa primeiro."
        else:
            lat_field.value = f"{lat:.6f}"
            lon_field.value = f"{lon:.6f}"
            msg.value = "Coordenadas importadas para o formulário."
            update_preview_from_fields()
        page.update()
        
    page.add(ft.Text("Registrar Animal Perdido", size=18),
             name, species, location, desc, contact,
             ft.Row([lat_field, lon_field]),
             ft.Row([ft.ElevatedButton("Importar coordenadas do mapa", on_click=fetch_picked_coords),
                     ft.ElevatedButton("Atualizar mapa", on_click=lambda e: (update_preview_from_fields())),
                     ft.ElevatedButton("Salvar Registro", on_click=do_register_lost),
                     ft.TextButton("Voltar", on_click=go_to_home_func)]),
             preview_image,
             preview_address,
             msg)
    page.update()

show_lost_registration = lost_registration_view
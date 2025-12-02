# views/lost_registration_view.py
import flet as ft
from models import LostAnimal, session_scope
from services.geocoding import geocode_address, reverse_geocode, build_static_map_url
from services.map_server import LAST_PICK

class LostRegistrationView(ft.UserControl):
    """View para o formulário de registro de animal perdido."""
    def __init__(self, page, state, show_snack, show_home):
        super().__init__()
        self.page = page
        self.state = state
        self.show_snack = show_snack
        self.show_home = show_home
        
        self.name = ft.TextField(label="Nome do animal")
        self.species = ft.TextField(label="Espécie (opcional)")
        self.location = ft.TextField(label="Onde foi perdido (endereço ou descrição)")
        self.desc = ft.TextField(label="Descrição do animal (opcional)")
        self.contact = ft.TextField(label="Contato (opcional)")
        self.lat_field = ft.TextField(label="Latitude (opcional)")
        self.lon_field = ft.TextField(label="Longitude (opcional)")
        self.msg = ft.Text("")
        
        self.preview_image = ft.Image(src="", width=600, height=300)
        self.preview_address = ft.Text("", selectable=True)

    def update_preview_from_fields(self, e=None):
        try:
            if self.lat_field.value.strip() and self.lon_field.value.strip():
                lat = float(self.lat_field.value.strip()); lon = float(self.lon_field.value.strip())
                self.preview_image.src = build_static_map_url(lat, lon)
                self.preview_address.value = reverse_geocode(lat, lon) or "Endereço não encontrado"
            else:
                self.preview_image.src = ""
                self.preview_address.value = ""
        except Exception:
            self.preview_image.src = ""
            self.preview_address.value = ""
            
        self.update() # Atualiza apenas o UserControl

    def do_register_lost(self, ev):
        if not self.name.value.strip():
            self.msg.value = "Nome é obrigatório"
            self.update()
            return

        lat = None; lon = None
        if self.lat_field.value.strip() and self.lon_field.value.strip():
            try:
                lat = float(self.lat_field.value.strip())
                lon = float(self.lon_field.value.strip())
            except:
                self.msg.value = "Formato de coordenadas inválido"
                self.update()
                return
        else:
            lat, lon = geocode_address(self.location.value.strip())

        with session_scope() as s:
            la = LostAnimal(
                name=self.name.value.strip(),
                species=self.species.value.strip() or None,
                lost_location=self.location.value.strip() or None,
                desc_animal=self.desc.value.strip() or None,
                contact=self.contact.value.strip() or None,
                owner_id=self.state["current_user"]["id"],
                latitude=lat,
                longitude=lon
            )
            s.add(la)
        
        self.show_snack("Animal perdido registrado.")
        # Limpar campos
        self.name.value = self.species.value = self.location.value = self.desc.value = self.contact.value = ""
        self.lat_field.value = self.lon_field.value = ""
        self.update_preview_from_fields()
        self.update()

    def fetch_picked_coords(self, ev):
        lat = LAST_PICK.get("lat")
        lon = LAST_PICK.get("lon")
        if lat is None or lon is None:
            self.msg.value = "Coordenadas não selecionadas ainda — clique no mapa primeiro."
        else:
            self.lat_field.value = f"{lat:.6f}"
            self.lon_field.value = f"{lon:.6f}"
            self.msg.value = "Coordenadas importadas para o formulário."
            self.update_preview_from_fields()
        self.update()

    def build(self):
        if not self.state["current_user"]:
            return ft.Container(ft.Text("Usuário não logado."))
        
        return ft.Column([
            ft.Text("Register Lost Animal", size=18),
            self.name, self.species, self.location, self.desc, self.contact,
            ft.Row([self.lat_field, self.lon_field]),
            ft.Row([
                ft.ElevatedButton("Atualizar coordenadas selecionadas", on_click=self.fetch_picked_coords),
                ft.ElevatedButton("Atualizar mapa", on_click=self.update_preview_from_fields),
                ft.ElevatedButton("Salvar", on_click=self.do_register_lost),
                ft.TextButton("Voltar", on_click=self.show_home)
            ]),
            self.preview_image,
            self.preview_address,
            self.msg
        ])
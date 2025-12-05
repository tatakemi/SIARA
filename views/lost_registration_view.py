import flet as ft
from flet_map import Map
from flet.security import encrypt, decrypt
import os
from database.session import Session
from database.models import LostAnimal, User
from views.components.map_component import create_map
from geopy.geocoders import Nominatim
import re

# Constantes e Variáveis Globais
APP_SECRET = os.environ.get("APP_SECRET", "super-secret-key-default")

# --- Funções Auxiliares ---

# Função para geocodificar o endereço
def geocode_address(address, show_snack_func):
    geolocator = Nominatim(user_agent="LostPetApp")
    try:
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude, location.address
        else:
            show_snack_func("Localização não encontrada. Tente um endereço mais específico.")
            return None, None, None
    except Exception as e:
        show_snack_func(f"Erro ao geocodificar: {e}")
        return None, None, None

# Função para reverter a geocodificação (coordenadas para endereço)
def reverse_geocode(lat, lon, show_snack_func):
    geolocator = Nominatim(user_agent="LostPetApp")
    try:
        location = geolocator.reverse((lat, lon))
        if location:
            return location.address
        else:
            return f"Lat: {lat}, Lon: {lon}"
    except Exception as e:
        show_snack_func(f"Erro ao obter endereço: {e}")
        return f"Lat: {lat}, Lon: {lon}"


# --- Componente Principal da View ---

def show_lost_registration(page, router, show_snack_func, editing_animal=None):
    # Dicionário de estado
    state = {
        "current_map": None,
        "is_editing": editing_animal is not None,
        "editing_animal_id": editing_animal.id if editing_animal else None,
        "current_lat": editing_animal.latitude if editing_animal else -25.43051,
        "current_lon": editing_animal.longitude if editing_animal else -49.278849,
        "initial_zoom": 13 if editing_animal else 13,
        "uploaded_file_name": None,
        "image_bytes": None,
        "image_url": editing_animal.image_url if editing_animal else None,
    }

    # Campos de formulário
    name = ft.TextField(label="Nome do Animal", value=editing_animal.name if editing_animal else "")
    species = ft.TextField(label="Espécie/Raça", value=editing_animal.species if editing_animal else "")
    location = ft.TextField(
        label="Localização onde foi perdido (endereço)",
        value=editing_animal.lost_location if editing_animal else "",
        on_submit=lambda e: geocode_and_update_map(e.control.value)
    )
    desc = ft.TextField(label="Descrição (Cor, Tamanho, Características)", value=editing_animal.desc_animal if editing_animal else "", multiline=True)
    contact = ft.TextField(label="Contato (Telefone/Email)", value=editing_animal.contact if editing_animal else "")
    
    # Campos ocultos para Lat/Lon
    lat_field = ft.TextField(label="Latitude", value=str(state["current_lat"]), read_only=True)
    lon_field = ft.TextField(label="Longitude", value=str(state["current_lon"]), read_only=True)

    # Componentes de Upload de Imagem
    preview_image = ft.Image(
        src=state["image_url"] if state["image_url"] else "https://placehold.co/150x150/EEEEEE/888888?text=Sem+Imagem",
        width=150,
        height=150,
        fit=ft.ImageFit.COVER,
        border_radius=ft.border_radius.all(10)
    )
    upload_status = ft.Text(
        value="Imagem carregada." if state["image_url"] else "Nenhuma imagem selecionada.", 
        size=12,
        color=ft.colors.ON_BACKGROUND
    )

    image_preview = ft.Container(
        content=preview_image,
        width=150,
        height=150,
        alignment=ft.alignment.center,
        border_radius=ft.border_radius.all(10)
    )

    def upload_image_and_update_preview(e: ft.FilePickerResultEvent):
        if e.files:
            file = e.files[0]
            if file.size > 2 * 1024 * 1024: # Limite de 2MB
                show_snack_func("A imagem é muito grande. Tamanho máximo: 2MB.")
                return

            with open(file.path, "rb") as f:
                state["image_bytes"] = f.read()
            
            # O Flet precisa de um path local para exibir a imagem, mesmo que
            # seja temporário. Como não podemos salvar arquivos no servidor
            # de forma persistente, vamos usar um hack: salvar os bytes e
            # usar o FilePickerResultEvent.path como src temporário.
            # No Flet Web, o path é um link temporário já carregado pelo navegador.
            
            preview_image.src = file.path
            state["uploaded_file_name"] = file.name
            upload_status.value = f"Pronto para enviar: {file.name}"
            page.update()
        else:
            upload_status.value = "Nenhuma imagem selecionada."
            page.update()

    file_picker = ft.FilePicker(on_result=upload_image_and_update_preview)
    page.overlay.append(file_picker)

    # --- Funções de Mapa e Geocodificação ---
    
    def on_map_created(e: ft.ControlEvent):
        state["current_map"] = e.control
        state["current_map"].controls.append(
            ft.MapMarker(
                latitude=state["current_lat"],
                longitude=state["current_lon"],
                content=ft.Icon(ft.icons.LOCATION_ON, color=ft.colors.RED_600, size=40),
            )
        )
        page.update()

    def on_map_click(e: ft.MapClickEvent):
        new_lat = e.latitude
        new_lon = e.longitude

        # Atualiza o estado
        state["current_lat"] = new_lat
        state["current_lon"] = new_lon
        
        # Atualiza os campos Lat/Lon
        lat_field.value = f"{new_lat:.6f}"
        lon_field.value = f"{new_lon:.6f}"

        # Geocodifica e atualiza o campo de endereço
        new_address = reverse_geocode(new_lat, new_lon, show_snack_func)
        location.value = new_address

        # Atualiza o marcador
        state["current_map"].controls.clear()
        state["current_map"].controls.append(
            ft.MapMarker(
                latitude=new_lat,
                longitude=new_lon,
                content=ft.Icon(ft.icons.LOCATION_ON, color=ft.colors.RED_600, size=40),
            )
        )
        page.update()

    def geocode_and_update_map(address):
        if not address:
            return
            
        lat, lon, full_address = geocode_address(address, show_snack_func)
        
        if lat is not None and lon is not None:
            # Atualiza o estado
            state["current_lat"] = lat
            state["current_lon"] = lon
            
            # Atualiza os campos Lat/Lon
            lat_field.value = f"{lat:.6f}"
            lon_field.value = f"{lon:.6f}"
            
            # Atualiza o campo de endereço (com o endereço completo do geocoder)
            location.value = full_address
            
            # Atualiza o mapa
            state["current_map"].center = ft.LatLng(lat, lon)
            state["current_map"].controls.clear()
            state["current_map"].controls.append(
                ft.MapMarker(
                    latitude=lat,
                    longitude=lon,
                    content=ft.Icon(ft.icons.LOCATION_ON, color=ft.colors.RED_600, size=40),
                )
            )
            page.update()
        else:
            location.value = address # Mantém o valor original se a geocodificação falhar
            page.update()

    # --- Funções de Submissão ---

    def is_valid_contact(contact_str):
        # Regex simples para validar telefone ou email
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        phone_regex = r"^[\d\s\-\(\)\+]{8,30}$" # Aceita dígitos, espaços, -, (), +

        return re.fullmatch(email_regex, contact_str) or re.fullmatch(phone_regex, contact_str)

    def save_post(e):
        if not all([name.value, species.value, location.value, desc.value, contact.value]):
            show_snack_func("Por favor, preencha todos os campos obrigatórios (Nome, Espécie, Local, Descrição e Contato).", color=ft.colors.RED_500)
            return

        if not is_valid_contact(contact.value):
            show_snack_func("O contato deve ser um telefone válido ou um email.", color=ft.colors.RED_500)
            return

        # Busca a sessão atual do usuário
        token = page.client_storage.get("user_session")
        if not token:
            show_snack_func("Sessão expirada. Faça login novamente.", color=ft.colors.RED_500)
            router.go("/login")
            return
            
        cur_user_data = decrypt(token, APP_SECRET).split("|")
        cur = {"id": int(cur_user_data[0]), "username": cur_user_data[1]}
        
        image_url = state["image_url"]

        # Se houver uma nova imagem em bytes, faz o upload (em um ambiente real)
        # Por enquanto, se houver bytes, criptografamos e usamos como URL temporário
        if state["image_bytes"]:
            # Em um ambiente real, você faria upload para S3/Firebase Storage aqui.
            # Por simplicidade e restrições do ambiente, vamos apenas criptografar os bytes
            # e usá-los como um URL "falso" para persistência no banco de dados.
            # Isso é uma simulação, pois não podemos salvar arquivos no servidor.
            try:
                encrypted_bytes = encrypt(state["image_bytes"].decode('latin-1'), APP_SECRET)
                image_url = f"flet-bytes-encoded:{state['uploaded_file_name']}|{encrypted_bytes}"
            except Exception as ex:
                show_snack_func(f"Erro ao processar imagem: {ex}", color=ft.colors.RED_500)
                return

        with Session() as s:
            if state["is_editing"]:
                # --- Modo Edição ---
                animal_to_update = s.query(LostAnimal).filter_by(id=state["editing_animal_id"], owner_id=cur["id"]).first()
                if animal_to_update:
                    animal_to_update.name = name.value
                    animal_to_update.species = species.value
                    animal_to_update.lost_location = location.value
                    animal_to_update.desc_animal = desc.value
                    animal_to_update.contact = contact.value
                    animal_to_update.latitude = state["current_lat"]
                    animal_to_update.longitude = state["current_lon"]
                    animal_to_update.image_url = image_url # Atualiza a URL (mesmo que seja a antiga ou a nova)
                    
                    s.commit()
                    show_snack_func("Animal perdido atualizado!")
                    router.go("/profile") # Volta para o perfil
                else:
                    show_snack_func("Erro: Animal não encontrado ou você não é o dono.", color=ft.colors.RED_500)

            else:
                # --- Modo Novo Registro ---
                new_post = LostAnimal(
                    name=name.value,
                    species=species.value,
                    lost_location=location.value,
                    desc_animal=desc.value,
                    contact=contact.value,
                    latitude=state["current_lat"],
                    longitude=state["current_lon"],
                    image_url=image_url,
                    owner_id=cur["id"]
                )

                s.add(new_post)
                s.commit()

                show_snack_func("Animal perdido registrado!")

                # resetar campos após sucesso
                name.value = ""
                species.value = ""
                location.value = ""
                desc.value = ""
                contact.value = ""
                lat_field.value = str(state["current_lat"]) # Mantém o último lat/lon, mas limpa a UI
                lon_field.value = str(state["current_lon"])
                preview_image.src = "https://placehold.co/150x150/EEEEEE/888888?text=Sem+Imagem"
                upload_status.value = "Nenhuma imagem selecionada."
                
                # Reseta o estado da imagem
                state["image_bytes"] = None
                state["uploaded_file_name"] = None
                state["image_url"] = None
                
                # Recria o componente da imagem para forçar a atualização da URL
                image_preview.content = ft.Image(
                    src="https://placehold.co/150x150/EEEEEE/888888?text=Sem+Imagem",
                    width=150,
                    height=150,
                    fit=ft.ImageFit.COVER,
                    border_radius=ft.border_radius.all(10)
                )

                page.update()

    # Layout da View
    page_content = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Registrar Animal Perdido" if not state["is_editing"] else "Editar Animal Perdido",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.PRIMARY
                ),
                
                # Coluna para inputs e imagem
                ft.Row(
                    [
                        # Coluna de inputs (esquerda)
                        ft.Column(
                            [
                                name,
                                species,
                                contact,
                                ft.Text("Descrição do Animal:", weight=ft.FontWeight.MEDIUM),
                                desc,
                            ],
                            expand=True,
                            spacing=15
                        ),
                        
                        # Upload de imagem (direita)
                        ft.Column(
                            [
                                ft.Text("Foto do Animal:", weight=ft.FontWeight.MEDIUM),
                                ft.Stack(
                                    [
                                        image_preview,
                                        ft.Container(
                                            content=ft.IconButton(
                                                icon=ft.icons.CAMERA_ALT_OUTLINED,
                                                icon_color=ft.colors.WHITE,
                                                tooltip="Selecionar Imagem",
                                                on_click=lambda _: file_picker.pick_files(
                                                    allow_multiple=False, 
                                                    allowed_extensions=["png", "jpg", "jpeg"]
                                                ),
                                            ),
                                            alignment=ft.alignment.center,
                                            opacity=0.8,
                                            bgcolor=ft.colors.BLACK54,
                                            border_radius=ft.border_radius.all(10)
                                        )
                                    ]
                                ),
                                upload_status,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER
                        )
                    ],
                    wrap=True,
                    vertical_alignment=ft.CrossAxisAlignment.START
                ),

                ft.Divider(height=20),
                
                ft.Text("Localização onde foi perdido:", weight=ft.FontWeight.BOLD),

                # Campos de Localização e Mapa
                ft.Row(
                    [
                        location,
                        ft.IconButton(
                            icon=ft.icons.SEARCH,
                            tooltip="Buscar Endereço",
                            on_click=lambda e: geocode_and_update_map(location.value)
                        )
                    ]
                ),

                # Campos Lat/Lon (Ocultos ou Apenas Leitura)
                ft.Row(
                    [
                        ft.Container(lat_field, expand=True),
                        ft.Container(lon_field, expand=True),
                    ],
                    spacing=10
                ),

                ft.Container(
                    content=Map(
                        ft.MapOptions(
                            center=ft.LatLng(state["current_lat"], state["current_lon"]),
                            zoom=state["initial_zoom"],
                            on_click=on_map_click,
                            on_map_created=on_map_created,
                            controls=[
                                ft.MapZoomControl(
                                    zoom_in_tooltip="Mais Zoom",
                                    zoom_out_tooltip="Menos Zoom",
                                    padding=ft.padding.all(10),
                                    alignment=ft.alignment.top_right
                                ),
                            ]
                        )
                    ),
                    height=400,
                    border_radius=ft.border_radius.all(10),
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=5, color=ft.colors.BLACK26)
                ),

                ft.Divider(height=20),

                # Botões de Ação
                ft.Row(
                    [
                        ft.ElevatedButton(
                            text="Salvar" if state["is_editing"] else "Registrar Perda",
                            icon=ft.icons.SAVE if state["is_editing"] else ft.icons.PETS,
                            on_click=save_post,
                            bgcolor=ft.colors.PRIMARY,
                            color=ft.colors.WHITE,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                        ),
                        ft.TextButton(
                            text="Cancelar",
                            on_click=lambda e: router.go("/profile") if state["is_editing"] else router.go("/"),
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                        )
                    ],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.CENTER
                )
            ],
            scroll=ft.ScrollMode.ADAPTIVE,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=25
        ),
        padding=20,
        alignment=ft.alignment.top_center,
        expand=True
    )
    
    return page_content

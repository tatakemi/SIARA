import flet as ft
from models import LostAnimal, session_scope 
from services.geocoding import geocode_address, reverse_geocode, build_static_map_url 
from services.map_server import LAST_PICK 
import os
import shutil
import time 

def show_lost_registration(page, state, go_to_home_func, show_snack_func):
    page.controls.clear()
    cur = state.get("current_user")
    if not cur:
        go_to_home_func()
        return

    # --- 1. CARREGAR DADOS PARA EDIÇÃO ---
    edit_id = state.get("edit_lost_id")
    current_post = None
    if edit_id is not None:
        try:
            with session_scope() as s:
                current_post = s.query(LostAnimal).filter_by(id=edit_id, owner_id=cur["id"]).first()
                if not current_post:
                    state["edit_lost_id"] = None
                    show_snack_func("Post para edição não encontrado.", is_error=True)
        except Exception as e:
            print(f"Erro ao carregar post para edição (Lost): {e}")
            current_post = None
            state["edit_lost_id"] = None
            show_snack_func("Erro ao carregar dados.", is_error=True)

    # --- 2. DEFINIÇÃO DE VARIÁVEIS DE ESTADO E HANDLERS ---

    title_text = "Registrar Animal Perdido" if not current_post else "Editar Post Perdido"
    button_text = "Registrar" if not current_post else "Atualizar"
    
    # VARIÁVEIS DE ESTADO DO UPLOAD
    file_path_chosen = None
    file_name_chosen = None

    # Campos de formulário
    name = ft.TextField(label="Nome do Animal", value=current_post.name if current_post else "")
    species = ft.TextField(label="Espécie/Raça", value=current_post.species if current_post else "")
    location = ft.TextField(label="Última Localização Vista (Ex: Endereço)", value=current_post.lost_location if current_post else "")
    desc = ft.TextField(label="Descrição do Animal (Características)", value=current_post.desc_animal if current_post else "", multiline=True)
    
    # CORREÇÃO APLICADA: Uso de .get("contact")
    contact = ft.TextField(label="Contato para Resgate (Telefone/Email)", 
                           value=current_post.contact if current_post else cur.get("contact") or "")
    
    # Coordenadas (opcional)
    lat_field = ft.TextField(label="Latitude", read_only=True, value=str(current_post.latitude) if current_post and current_post.latitude is not None else "")
    lon_field = ft.TextField(label="Longitude", read_only=True, value=str(current_post.longitude) if current_post and current_post.longitude is not None else "")
    
    # Controle para a URL da imagem atual (apenas para edição)
    current_image_url = current_post.image_url if current_post else None

    # Visualização do mapa estático
    preview_image = ft.Image(src=build_static_map_url(float(lat_field.value), float(lon_field.value)) if lat_field.value else "", 
                             width=300, height=200, fit=ft.ImageFit.CONTAIN)
    
    # Controle para exibir o nome do arquivo escolhido ou a imagem atual
    upload_status_text = ft.Text(f"Imagem atual: {current_image_url.split('/')[-1]}" if current_image_url else "Nenhuma imagem selecionada.", size=10)
    
    # Controles
    msg = ft.Text("", color=ft.Colors.RED)

    # File Picker
    def file_picker_result(e: ft.FilePickerResultEvent):
        nonlocal file_path_chosen, file_name_chosen
        
        if e.files:
            file_path_chosen = e.files[0].path
            file_name_chosen = e.files[0].name
            upload_status_text.value = f"Arquivo selecionado: {file_name_chosen}"
        else:
            file_path_chosen = None
            file_name_chosen = None
            upload_status_text.value = "Seleção cancelada ou falha."
            
        page.update()

    file_picker = ft.FilePicker(on_result=file_picker_result)
    page.overlay.append(file_picker)

    def update_preview_from_fields():
        """Atualiza a imagem de pré-visualização do mapa."""
        try:
            lat = float(lat_field.value) if lat_field.value else None
            lon = float(lon_field.value) if lon_field.value else None
            
            if lat is not None and lon is not None:
                preview_image.src = build_static_map_url(lat, lon, zoom=14, width=300, height=200, marker="red-pushpin")
            else:
                preview_image.src = ""
                
            page.update()
        except ValueError:
            preview_image.src = ""
            page.update()

    def fetch_picked_coords(e):
        """Busca as coordenadas do mapa (LAST_PICK) e atualiza os campos."""
        lat = LAST_PICK["lat"]
        lon = LAST_PICK["lon"]
        
        if lat is not None and lon is not None:
            lat_field.value = f"{lat:.6f}"
            lon_field.value = f"{lon:.6f}"
            
            address = reverse_geocode(lat, lon)
            if address and not location.value:
                location.value = address
                
            update_preview_from_fields()
        else:
            show_snack_func("Nenhuma coordenada selecionada no mapa.", is_error=True)
            page.update()

    # --- 3. LÓGICA DE PERSISTÊNCIA ---
    def do_register_lost(e):
        # Declarações nonlocal no topo
        nonlocal current_post, current_image_url, file_path_chosen, file_name_chosen
        
        msg.value = ""
        
        # Validação manual dos campos obrigatórios
        if not name.value or not location.value or not contact.value:
            msg.value = "Por favor, preencha todos os campos obrigatórios (Nome, Localização, Contato)."
            page.update()
            return
        
        # Geocodificação
        lat, lon = None, None
        try:
            lat = float(lat_field.value) if lat_field.value else None
            lon = float(lon_field.value) if lon_field.value else None
        except ValueError:
            lat, lon = None, None

        if (current_post and location.value != current_post.lost_location) or (not current_post and (lat is None or lon is None)):
            geo_lat, geo_lon = geocode_address(location.value)
            if geo_lat is not None:
                lat = geo_lat
                lon = geo_lon
                lat_field.value = f"{lat:.6f}"
                lon_field.value = f"{lon:.6f}"
            elif lat is None or lon is None:
                msg.value = "Não foi possível encontrar as coordenadas para o endereço fornecido. Por favor, seja mais específico ou use o mapa."
                page.update()
                return

        # Lógica de Upload de Imagem
        image_url_to_save = current_image_url

        if file_path_chosen and file_name_chosen:
            save_dir = os.path.join(os.getcwd(), 'static', 'images')
            os.makedirs(save_dir, exist_ok=True)
            
            timestamp = int(time.time()) 
            base_name, ext = os.path.splitext(file_name_chosen)
            safe_name = f"lost_{cur['id']}_{timestamp}{ext}"
            final_path = os.path.join(save_dir, safe_name)
            
            try:
                shutil.copyfile(file_path_chosen, final_path)
                image_url_to_save = f"static/images/{safe_name}"
            except Exception as err:
                msg.value = f"Erro ao salvar arquivo: {err}"
                page.update()
                return

        # Lógica de persistência no DB
        try:
            with session_scope() as s:
                if current_post:
                    # Modo Edição
                    current_post.name = name.value
                    current_post.species = species.value
                    current_post.lost_location = location.value
                    current_post.desc_animal = desc.value
                    current_post.contact = contact.value
                    current_post.latitude = lat
                    current_post.longitude = lon
                    current_post.image_url = image_url_to_save
                    s.merge(current_post)
                    
                    is_edit_mode = True
                else:
                    # Modo Registro
                    new_animal = LostAnimal(
                        name=name.value,
                        species=species.value,
                        lost_location=location.value,
                        desc_animal=desc.value,
                        contact=contact.value,
                        latitude=lat,
                        longitude=lon,
                        owner_id=cur["id"],
                        image_url=image_url_to_save
                    )
                    s.add(new_animal)
                    is_edit_mode = False
                    
            if is_edit_mode:
                state["edit_lost_id"] = None
                show_snack_func("Animal perdido atualizado com sucesso!")
                go_to_home_func()
            else:
                show_snack_func("Animal perdido registrado.")
                # Limpa campos
                name.value = species.value = location.value = desc.value = contact.value = ""
                lat_field.value = lon_field.value = ""
                
                # Reseta as variáveis de estado do upload
                file_path_chosen = None
                file_name_chosen = None
                upload_status_text.value = "Nenhuma imagem selecionada."
                
                update_preview_from_fields()
                
        except Exception as e:
            print(f"Erro ao salvar post (Lost): {e}")
            msg.value = f"Erro ao salvar: {e}"
            page.update()
        
    # --- 5. LAYOUT ---
    page.add(
        ft.Text(title_text, size=18, weight=ft.FontWeight.BOLD),
        name, species, location, desc, contact,
        ft.Row([lat_field, lon_field]),
        ft.Row([
            ft.ElevatedButton("Importar coordenadas do mapa", on_click=fetch_picked_coords),
            ft.ElevatedButton("Atualizar mapa", on_click=lambda e: (update_preview_from_fields())),
        ], wrap=True),
        # Controles de upload
        ft.Container(height=10),
        ft.Text("Upload de Imagem:", weight=ft.FontWeight.BOLD),
        ft.Row([
            ft.ElevatedButton(
                "Escolher Imagem...",
                icon=ft.Icons.UPLOAD_FILE,
                on_click=lambda _: file_picker.pick_files(
                    allow_multiple=False,
                    allowed_extensions=["jpg", "jpeg", "png", "gif"]
                ),
            ),
            upload_status_text,
        ]),
        ft.Container(height=10),
        # Preview e botões
        preview_image,
        msg,
        ft.Row([
            ft.ElevatedButton(button_text, on_click=do_register_lost, 
                              style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)),
            ft.ElevatedButton("Voltar", on_click=go_to_home_func, style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE))
        ])
    )
    
    update_preview_from_fields()
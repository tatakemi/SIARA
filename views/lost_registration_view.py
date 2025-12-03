# lost_registration_view.py

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

    # --- 1. CARREGAR DADOS PARA EDIÇÃO (CORREÇÃO DetachedInstanceError) ---
    # Os dados já foram carregados e serializados em app.py antes de chamar esta view.
    edit_id = state.get("edit_lost_id")
    current_post_data = state.get("post_data_for_edit")
    
    is_edit_mode = edit_id is not None and current_post_data is not None
    
    # Validação de falha no carregamento (só deve ocorrer se houver erro em app.py)
    if edit_id is not None and not is_edit_mode:
        show_snack_func("Falha ao carregar dados para edição. Tente novamente.", is_error=True)
        state["edit_lost_id"] = None
        state["post_data_for_edit"] = None
        go_to_home_func()
        return

    # --- 2. DEFINIÇÃO DE VARIÁVEIS DE ESTADO E HANDLERS ---

    title_text = "Registrar Animal Perdido" if not is_edit_mode else "Editar Post Perdido"
    button_text = "Registrar" if not is_edit_mode else "Atualizar"
    
    # VARIÁVEIS DE ESTADO DO UPLOAD
    file_path_chosen = None
    file_name_chosen = None

    # Campos de formulário - Usando current_post_data.get('attr', default)
    name = ft.TextField(label="Nome do Animal", value=current_post_data.get('name', '') if is_edit_mode else "")
    species = ft.TextField(label="Espécie/Raça", value=current_post_data.get('species', '') if is_edit_mode else "")
    location = ft.TextField(label="Última Localização Vista (Ex: Endereço)", value=current_post_data.get('lost_location', '') if is_edit_mode else "")
    desc = ft.TextField(label="Descrição do Animal (Características)", value=current_post_data.get('desc_animal', '') if is_edit_mode else "", multiline=True)
    
    # Contato: Prioriza o contato salvo, senão usa o contato do usuário
    contact_value = current_post_data.get('contact', '') if is_edit_mode else cur.get("contact", "")
    contact = ft.TextField(label="Contato para Resgate (Telefone/Email)", value=contact_value)
    
    # Coordenadas (opcional)
    lat_val = str(current_post_data['latitude']) if is_edit_mode and current_post_data.get('latitude') is not None else ""
    lon_val = str(current_post_data['longitude']) if is_edit_mode and current_post_data.get('longitude') is not None else ""
    
    lat_field = ft.TextField(label="Latitude", read_only=True, value=lat_val)
    lon_field = ft.TextField(label="Longitude", read_only=True, value=lon_val)
    
    # Controle para a URL da imagem atual (apenas para edição)
    current_image_url = current_post_data.get('image_url') if is_edit_mode else None

    # Visualização do mapa estático
    preview_image = ft.Image(src=build_static_map_url(float(lat_field.value), float(lon_field.value)) if lat_field.value else "", 
                             width=300, height=200, fit=ft.ImageFit.CONTAIN)
    
    # Controle para exibir o nome do arquivo escolhido ou a imagem atual
    display_name = current_image_url.split('/')[-1] if current_image_url else "Nenhuma imagem selecionada."
    upload_status_text = ft.Text(f"Imagem atual: {display_name}" if current_image_url else "Nenhuma imagem selecionada.", size=10)
    
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
        # Declarações nonlocal
        nonlocal current_image_url, file_path_chosen, file_name_chosen
        msg.value = ""

        # Validação manual dos campos obrigatórios
        if not name.value or not location.value or not contact.value:
            msg.value = "Por favor, preencha todos os campos obrigatórios (Nome, Localização, Contato)."
            page.update()
            return

        # Geocodificação
        lat = float(lat_field.value) if lat_field.value else None
        lon = float(lon_field.value) if lon_field.value else None
        
        # Se não há coordenadas, tenta geocodificar o endereço
        if lat is None or lon is None:
            coords = geocode_address(location.value)
            if coords:
                lat, lon = coords
            else:
                lat = lon = None
                show_snack_func("Não foi possível obter coordenadas para a localização. Por favor, use o mapa.", is_error=True)
                page.update()
                return # Impede o registro se a localização for crítica

        # Upload e URL da imagem
        image_url_to_save = current_image_url
        if file_path_chosen:
            # Lógica de upload (assumindo que salva o arquivo e retorna a URL)
            try:
                # Exemplo: Simulação de upload para a pasta `map_static`
                filename_to_save = f"{cur['id']}_{int(time.time())}_{file_name_chosen}"
                target_path = os.path.join(os.getcwd(), "map_static", filename_to_save)
                shutil.copyfile(file_path_chosen, target_path)
                image_url_to_save = f"/map_static/{filename_to_save}" # URL acessível pelo servidor local
            except Exception as up_ex:
                print(f"Erro ao salvar arquivo de imagem: {up_ex}")
                show_snack_func("Erro ao salvar imagem. Registrando sem imagem.", is_error=True)
                image_url_to_save = current_image_url # Mantém a antiga ou None
        
        try:
            with session_scope() as s:
                if is_edit_mode:
                    # Lógica de Atualização (UPDATE)
                    post_to_update = s.query(LostAnimal).filter_by(id=edit_id, owner_id=cur["id"]).first()
                    if post_to_update:
                        post_to_update.name = name.value
                        post_to_update.species = species.value
                        post_to_update.lost_location = location.value
                        post_to_update.desc_animal = desc.value
                        post_to_update.contact = contact.value
                        post_to_update.latitude = lat
                        post_to_update.longitude = lon
                        post_to_update.image_url = image_url_to_save
                        
                        s.commit() 
                        
                        # Limpa flags de estado (CRÍTICO)
                        state["edit_lost_id"] = None
                        state["post_data_for_edit"] = None
                        show_snack_func("Animal perdido atualizado com sucesso!")
                        go_to_home_func()
                    else:
                        msg.value = "Erro: Postagem para edição não encontrada."
                        page.update()
                else:
                    # Lógica de Inserção (CREATE)
                    new_post = LostAnimal(
                        name=name.value,
                        species=species.value,
                        lost_location=location.value,
                        desc_animal=desc.value,
                        contact=contact.value,
                        latitude=lat,
                        longitude=lon,
                        image_url=image_url_to_save,
                        owner_id=cur["id"]
                    )
                    s.add(new_post)
                    s.commit()
                    
                    show_snack_func("Animal perdido registrado.")
                    # Limpa campos
                    name.value = species.value = location.value = desc.value = contact.value = ""
                    lat_field.value = lon_field.value = ""
                    # Reseta as variáveis de estado do upload
                    file_path_chosen = None
                    file_name_chosen = None
                    upload_status_text.value = "Nenhuma imagem selecionada."
                    preview_image.src = "" # Limpa a preview
                    page.update()

        except Exception as e:
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
                              style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600)),
            ft.OutlinedButton("Voltar", on_click=go_to_home_func)
        ], alignment=ft.MainAxisAlignment.END)
    )
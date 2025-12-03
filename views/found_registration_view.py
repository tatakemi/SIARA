# found_registration_view.py

import flet as ft
from models import FoundReport, session_scope 
from services.geocoding import geocode_address, reverse_geocode, build_static_map_url 
from services.map_server import LAST_PICK 
import os
import shutil
import time
from datetime import datetime # NOVO: Import necessário para o parsing da data

def show_found_registration(page, state, go_to_home_func, show_snack_func):
    page.controls.clear()
    cur = state.get("current_user")
    if not cur:
        go_to_home_func()
        return

    # --- 1. CARREGAR DADOS PARA EDIÇÃO (CORREÇÃO DetachedInstanceError) ---
    # Os dados já foram carregados e serializados em app.py antes de chamar esta view.
    edit_id = state.get("edit_found_id")
    current_post_data = state.get("post_data_for_edit")
    
    is_edit_mode = edit_id is not None and current_post_data is not None
    
    # Validação de falha no carregamento (só deve ocorrer se houver erro em app.py)
    if edit_id is not None and not is_edit_mode:
        show_snack_func("Falha ao carregar dados para edição. Tente novamente.", is_error=True)
        state["edit_found_id"] = None
        state["post_data_for_edit"] = None
        go_to_home_func()
        return

    # --- 2. DEFINIÇÃO DE VARIÁVEIS DE ESTADO E HANDLERS ---
    
    title_text = "Relatar Animal Encontrado" if not is_edit_mode else "Editar Relato Encontrado"
    button_text = "Relatar" if not is_edit_mode else "Atualizar"

    # VARIÁVEIS DE ESTADO DO UPLOAD
    file_path_chosen = None
    file_name_chosen = None
    
    # Campos de formulário - Usando current_post_data.get('attr', default)
    species = ft.TextField(label="Espécie/Raça do Animal Encontrado", value=current_post_data.get('species', '') if is_edit_mode else "")
    location = ft.TextField(label="Local onde o animal foi encontrado", value=current_post_data.get('found_location', '') if is_edit_mode else "")
    # A data já vem formatada como string (ou vazia) do app.py
    date_val = current_post_data.get('found_date', '') if is_edit_mode else ""
    date = ft.TextField(label="Data que o animal foi encontrado (DD/MM/AAAA)", value=date_val)
    desc = ft.TextField(label="Descrição do animal e circunstâncias do encontro", value=current_post_data.get('found_description', '') if is_edit_mode else "", multiline=True)
    
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
                preview_image.src = build_static_map_url(lat, lon, zoom=14, width=300, height=200, marker="green-pushpin")
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
    def do_register_found(e):
        # Declarações nonlocal
        nonlocal current_image_url, file_path_chosen, file_name_chosen
        msg.value = ""

        # Validação manual dos campos obrigatórios
        if not species.value or not location.value:
            msg.value = "Por favor, preencha a Espécie e o Local de Encontro (campos obrigatórios)."
            page.update()
            return
            
        # Parse da data
        found_date_parsed = None
        if date.value:
            try:
                found_date_parsed = datetime.strptime(date.value, '%d/%m/%Y').date()
            except ValueError:
                msg.value = "Formato de data inválido. Use DD/MM/AAAA."
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
                lat = lon = None # Permite registro sem coordenadas, mas com aviso se falhar
                show_snack_func("Não foi possível obter coordenadas para a localização. Por favor, use o mapa, se possível.", is_error=True)
                page.update()

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
                    post_to_update = s.query(FoundReport).filter_by(id=edit_id, finder_id=cur["id"]).first()
                    if post_to_update:
                        post_to_update.species = species.value
                        post_to_update.found_location = location.value
                        post_to_update.found_description = desc.value
                        post_to_update.found_date = found_date_parsed
                        post_to_update.latitude = lat
                        post_to_update.longitude = lon
                        post_to_update.image_url = image_url_to_save
                        
                        s.commit()
                        
                        # Limpa flags de estado (CRÍTICO)
                        state["edit_found_id"] = None
                        state["post_data_for_edit"] = None
                        show_snack_func("Relato de animal encontrado atualizado com sucesso!")
                        go_to_home_func()
                    else:
                        msg.value = "Erro: Relato para edição não encontrado."
                        page.update()
                else:
                    # Lógica de Inserção (CREATE)
                    new_post = FoundReport(
                        species=species.value,
                        found_description=desc.value,
                        found_location=location.value,
                        found_date=found_date_parsed,
                        latitude=lat,
                        longitude=lon,
                        image_url=image_url_to_save,
                        finder_id=cur["id"]
                    )
                    s.add(new_post)
                    s.commit()
                    
                    show_snack_func("Registro de animal encontrado salvo.")
                    # Limpa campos
                    species.value = location.value = date.value = desc.value = ""
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
        species, location, date, desc,
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
            ft.ElevatedButton(button_text, on_click=do_register_found, 
                              style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_600)),
            ft.OutlinedButton("Voltar", on_click=go_to_home_func)
        ], alignment=ft.MainAxisAlignment.END)
    )
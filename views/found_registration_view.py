# found_registration_view.py

import flet as ft
from models import FoundReport, session_scope
from services.geocoding import geocode_address, reverse_geocode, build_static_map_url
import os
import shutil
import time
from datetime import datetime


def show_found_registration(page, state, go_to_home_func, show_snack_func, go_to_map_func):
    page.controls.clear()
    cur = state.get("current_user")

    state["return_to"] = "found_reg"

    if not cur:
        go_to_home_func()
        return

    # ---------- 1. CARREGAR DADOS PARA EDIÇÃO ----------
    edit_id = state.get("edit_found_id")
    current_post_data = state.get("post_data_for_edit")

    is_edit_mode = edit_id is not None and current_post_data is not None

    if edit_id is not None and not is_edit_mode:
        show_snack_func("Falha ao carregar dados para edição.", is_error=True)
        state["edit_found_id"] = None
        state["post_data_for_edit"] = None
        go_to_home_func()
        return

    # ---------- 2. CAMPOS DO FORMULÁRIO ----------
    title_text = "Relatar Animal Encontrado" if not is_edit_mode else "Editar Relato Encontrado"
    button_text = "Relatar" if not is_edit_mode else "Atualizar"

    file_path_chosen = None
    file_name_chosen = None

    species = ft.TextField(
        label="Espécie/Raça do Animal Encontrado",
        value=current_post_data.get("species", "") if is_edit_mode else ""
    )

    location = ft.TextField(
        label="Local onde o animal foi encontrado",
        value=current_post_data.get("found_location", "") if is_edit_mode else ""
    )

    date_val = current_post_data.get("found_date", "") if is_edit_mode else ""
    date = ft.TextField(label="Data do Encontro (DD/MM/AAAA)", value=date_val)

    desc = ft.TextField(
        label="Descrição do animal e circunstâncias",
        value=current_post_data.get("found_description", "") if is_edit_mode else "",
        multiline=True
    )

    lat_val = str(current_post_data["latitude"]) if is_edit_mode and current_post_data.get("latitude") else ""
    lon_val = str(current_post_data["longitude"]) if is_edit_mode and current_post_data.get("longitude") else ""

    lat_field = ft.TextField(label="Latitude", value=lat_val, read_only=True)
    lon_field = ft.TextField(label="Longitude", value=lon_val, read_only=True)

    current_image_url = current_post_data.get("image_url") if is_edit_mode else None

    preview_image = ft.Image(
        src=build_static_map_url(float(lat_val), float(lon_val)) if lat_val else "",
        width=300,
        height=200,
        fit=ft.ImageFit.CONTAIN
    )

    display_name = current_image_url.split("/")[-1] if current_image_url else "Nenhuma imagem selecionada."
    upload_status_text = ft.Text(
        f"Imagem atual: {display_name}" if current_image_url else "Nenhuma imagem selecionada.",
        size=10
    )

    msg = ft.Text("", color=ft.Colors.RED)

    # ---------- File Picker ----------
    def file_picker_result(e: ft.FilePickerResultEvent):
        nonlocal file_path_chosen, file_name_chosen
        if e.files:
            file_path_chosen = e.files[0].path
            file_name_chosen = e.files[0].name
            upload_status_text.value = f"Arquivo selecionado: {file_name_chosen}"
        else:
            file_path_chosen = None
            file_name_chosen = None
            upload_status_text.value = "Nenhuma imagem selecionada."

        page.update()

    file_picker = ft.FilePicker(on_result=file_picker_result)
    page.overlay.append(file_picker)

    # ---------- 3. ATUALIZAÇÃO DO MAPA ----------
    def update_preview_from_fields():
        try:
            if lat_field.value and lon_field.value:
                preview_image.src = build_static_map_url(
                    float(lat_field.value),
                    float(lon_field.value),
                    zoom=14,
                    width=300,
                    height=200,
                    marker="green-pushpin",
                )
            else:
                preview_image.src = ""
        except:
            preview_image.src = ""

        page.update()

    # ---------- 4. BUSCAR COORDENADAS SELECIONADAS NO MAPA ----------
    coords = state.get("picked_coords")
    if coords:
        lat, lon = coords
        lat_field.value = f"{lat:.6f}"
        lon_field.value = f"{lon:.6f}"

        # preencher o endereço automaticamente se vazio
        if not location.value:
            address = reverse_geocode(lat, lon)
            if address:
                location.value = address

        update_preview_from_fields()

    # ---------- 5. SALVAR ----------
    def do_register_found(e):
        nonlocal current_image_url, file_path_chosen, file_name_chosen
        msg.value = ""

        if not species.value or not location.value:
            msg.value = "Espécie e Local são obrigatórios."
            page.update()
            return

        # Data
        found_date_parsed = None
        if date.value:
            try:
                found_date_parsed = datetime.strptime(date.value, "%d/%m/%Y").date()
            except ValueError:
                msg.value = "Data inválida. Use DD/MM/AAAA."
                page.update()
                return

        # Coordenadas
        lat = float(lat_field.value) if lat_field.value else None
        lon = float(lon_field.value) if lon_field.value else None

        if lat is None or lon is None:
            coords = geocode_address(location.value)
            if coords:
                lat, lon = coords
            else:
                show_snack_func("Não foi possível obter coordenadas. Use o mapa.", is_error=True)

        # Upload da imagem
        image_url_to_save = current_image_url
        if file_path_chosen:
            try:
                filename_to_save = f"{cur['id']}_{int(time.time())}_{file_name_chosen}"
                target_path = os.path.join(os.getcwd(), "static/images", filename_to_save)
                shutil.copyfile(file_path_chosen, target_path)
                image_url_to_save = f"/images/{filename_to_save}"
            except:
                show_snack_func("Erro ao salvar imagem.", is_error=True)

        # Persistência
        try:
            with session_scope() as s:
                if is_edit_mode:
                    post = s.query(FoundReport).filter_by(id=edit_id, finder_id=cur["id"]).first()
                    if post:
                        post.species = species.value
                        post.found_location = location.value
                        post.found_description = desc.value
                        post.found_date = found_date_parsed
                        post.latitude = lat
                        post.longitude = lon
                        post.image_url = image_url_to_save
                        s.commit()

                        state["edit_found_id"] = None
                        state["post_data_for_edit"] = None

                        show_snack_func("Relato atualizado.")
                        go_to_home_func()
                        return

                # CREATE
                new_report = FoundReport(
                    species=species.value,
                    found_description=desc.value,
                    found_location=location.value,
                    found_date=found_date_parsed,
                    latitude=lat,
                    longitude=lon,
                    image_url=image_url_to_save,
                    finder_id=cur["id"],
                )

                s.add(new_report)
                s.commit()

                show_snack_func("Relato registrado!")

                species.value = location.value = date.value = desc.value = ""
                lat_field.value = lon_field.value = ""
                upload_status_text.value = "Nenhuma imagem selecionada."
                preview_image.src = ""
                page.update()

        except Exception as ex:
            msg.value = f"Erro ao salvar: {ex}"
            page.update()

    # ---------- 6. LAYOUT ----------
    page.add(
        ft.Text(title_text, size=18, weight=ft.FontWeight.BOLD),

        species,
        location,
        date,
        desc,

        ft.Row([
            lat_field,
            lon_field,
            ft.ElevatedButton(
                "Selecionar no Mapa",
                icon=ft.Icons.MAP,
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_200),
                on_click=lambda e: go_to_map_func(),
            )
        ]),

        ft.Container(height=10),
        ft.Text("Upload de Imagem:", weight=ft.FontWeight.BOLD),

        ft.Row([
            ft.ElevatedButton(
                "Escolher Imagem",
                icon=ft.Icons.UPLOAD_FILE,
                on_click=lambda _: file_picker.pick_files(
                    allow_multiple=False,
                    allowed_extensions=["jpg", "jpeg", "png", "gif"]
                ),
            ),
            upload_status_text,
        ]),

        ft.Container(height=10),

        preview_image,
        msg,

        ft.Row([
            ft.ElevatedButton(
                button_text,
                on_click=do_register_found,
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_600),
            ),
            ft.OutlinedButton("Voltar", on_click=go_to_home_func)
        ], alignment=ft.MainAxisAlignment.END),
    )

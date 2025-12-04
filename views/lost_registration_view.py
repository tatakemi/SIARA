import flet as ft
from models import LostAnimal, session_scope
from services.geocoding import geocode_address, reverse_geocode, build_static_map_url
import os
import shutil
import time


def show_lost_registration(page, state, go_to_home_func, show_snack_func, go_to_map_func):
    page.controls.clear()
    cur = state.get("current_user")
    state["return_to"] = "lost_reg"

    if not cur:
        go_to_home_func()
        return

    # ====================================================
    # 1) Carregar dados de edição (já serializados em app.py)
    # ====================================================

    edit_id = state.get("edit_lost_id")
    post_data = state.get("post_data_for_edit")

    is_edit = edit_id is not None and post_data is not None

    if edit_id and not post_data:
        show_snack_func("Erro ao carregar dados para edição.", is_error=True)
        state["edit_lost_id"] = None
        state["post_data_for_edit"] = None
        go_to_home_func()
        return

    title = "Registrar Animal Perdido" if not is_edit else "Editar Post Perdido"
    button_text = "Registrar" if not is_edit else "Salvar Alterações"

    # ====================================================
    # 2) Campos de formulário
    # ====================================================

    name = ft.TextField(label="Nome do animal", value=post_data.get("name", "") if is_edit else "")
    species = ft.TextField(label="Espécie / Raça", value=post_data.get("species", "") if is_edit else "")
    location = ft.TextField(label="Última Localização Vista", value=post_data.get("lost_location", "") if is_edit else "")
    desc = ft.TextField(label="Descrição", multiline=True,
                        value=post_data.get("desc_animal", "") if is_edit else "")

    contact_val = post_data.get("contact") if is_edit else cur.get("contact", "")
    contact = ft.TextField(label="Contato", value=contact_val)

    # Coordenadas
    lat_field = ft.TextField(
        label="Latitude", read_only=True,
        value=str(post_data.get("latitude")) if is_edit and post_data.get("latitude") else ""
    )

    lon_field = ft.TextField(
        label="Longitude", read_only=True,
        value=str(post_data.get("longitude")) if is_edit and post_data.get("longitude") else ""
    )

    # ====================================================
    # 3) Mapa Preview
    # ====================================================

    preview_image = ft.Image(
        src=build_static_map_url(float(lat_field.value), float(lon_field.value)) if lat_field.value else "",
        width=300, height=200, fit=ft.ImageFit.CONTAIN
    )

    def update_preview_from_fields():
        """Atualiza a imagem estática do mapa com base em lat/lon."""
        try:
            if lat_field.value and lon_field.value:
                lat = float(lat_field.value)
                lon = float(lon_field.value)
                preview_image.src = build_static_map_url(
                    lat, lon, zoom=15, width=300, height=200, marker="red-pushpin"
                )
            else:
                preview_image.src = ""
            page.update()
        except:
            preview_image.src = ""
            page.update()

    # ====================================================
    # 4) Se voltou do mapa — puxa coordenadas + endereço
    # ====================================================

    picked = state.get("picked_coords")
    if picked:
        lat, lon = picked
        lat_field.value = f"{lat:.6f}"
        lon_field.value = f"{lon:.6f}"

        # Reverse geocode → atualizar campo de localização
        addr = reverse_geocode(lat, lon)
        if addr:
            location.value = addr

        update_preview_from_fields()

    # ====================================================
    # 5) Upload de imagem
    # ====================================================

    file_path_chosen = None
    file_name_chosen = None

    current_image_url = post_data.get("image_url") if is_edit else None

    upload_status = ft.Text(
        f"Imagem atual: {current_image_url.split('/')[-1]}" if current_image_url else "Nenhuma imagem selecionada."
    )

    def file_picker_result(e: ft.FilePickerResultEvent):
        nonlocal file_path_chosen, file_name_chosen

        if e.files:
            file_path_chosen = e.files[0].path
            file_name_chosen = e.files[0].name
            upload_status.value = f"Selecionado: {file_name_chosen}"
        else:
            upload_status.value = "Nenhuma imagem selecionada."

        page.update()

    file_picker = ft.FilePicker(on_result=file_picker_result)
    page.overlay.append(file_picker)

    # ====================================================
    # 6) Botão para abrir o mapa
    # ====================================================

    def open_map(e):
        state["return_to"] = "lost_reg"
        go_to_map_func()

    # ====================================================
    # 7) Lógica de gravação
    # ====================================================

    msg = ft.Text("", color=ft.Colors.RED)

    def do_register_lost(e):
        nonlocal current_image_url, file_path_chosen, file_name_chosen

        if not name.value or not location.value or not contact.value:
            msg.value = "Preencha Nome, Localização e Contato."
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
                return

        # Upload
        image_url = current_image_url
        if file_path_chosen:
            try:
                filename = f"{cur['id']}_{int(time.time())}_{file_name_chosen}"
                target = os.path.join(os.getcwd(), "static/images", filename)
                shutil.copyfile(file_path_chosen, target)
                image_url = f"/images/{filename}"
            except Exception as ex:
                print("Erro upload:", ex)
                show_snack_func("Falha ao salvar imagem.", is_error=True)

        # Gravação no banco
        try:
            with session_scope() as s:
                if is_edit:
                    post = s.query(LostAnimal).filter_by(id=edit_id, owner_id=cur["id"]).first()
                    if not post:
                        msg.value = "Post não encontrado."
                        page.update()
                        return

                    post.name = name.value
                    post.species = species.value
                    post.lost_location = location.value
                    post.desc_animal = desc.value
                    post.contact = contact.value
                    post.latitude = lat
                    post.longitude = lon
                    post.image_url = image_url

                    s.commit()

                    state["edit_lost_id"] = None
                    state["post_data_for_edit"] = None
                    show_snack_func("Post atualizado!")
                    go_to_home_func()

                else:
                    new_post = LostAnimal(
                        name=name.value,
                        species=species.value,
                        lost_location=location.value,
                        desc_animal=desc.value,
                        contact=contact.value,
                        latitude=lat,
                        longitude=lon,
                        image_url=image_url,
                        owner_id=cur["id"]
                    )

                    s.add(new_post)
                    s.commit()

                    show_snack_func("Animal perdido registrado!")

                    # resetar campos
                    name.value = ""
                    species.value = ""
                    location.value = ""
                    desc.value = ""
                    contact.value = ""
                    lat_field.value = ""
                    lon_field.value = ""
                    preview_image.src = ""
                    upload_status.value = "Nenhuma imagem selecionada."

                    page.update()

        except Exception as ex:
            msg.value = f"Erro ao salvar: {ex}"
            page.update()

    # ====================================================
    # 8) Layout final
    # ====================================================

    page.add(
        ft.Text(title, size=22, weight=ft.FontWeight.BOLD),

        name,
        species,
        location,
        desc,
        contact,

        ft.Row([
            lat_field,
            lon_field,
            ft.ElevatedButton(
                "Selecionar no mapa",
                icon=ft.Icons.MAP,
                on_click=open_map,
                style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_200),
            ),
        ], alignment=ft.MainAxisAlignment.START),

        preview_image,

        ft.Text("Upload de imagem:", weight=ft.FontWeight.BOLD),
        upload_status,
        ft.ElevatedButton("Escolher imagem", on_click=lambda e: file_picker.pick_files(allow_multiple=False)),

        msg,

        ft.Row([
            ft.ElevatedButton(
                button_text,
                on_click=do_register_lost,
                style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600)
            ),
            ft.OutlinedButton("Voltar", on_click=lambda e: go_to_home_func())
        ], alignment=ft.MainAxisAlignment.END)
    )

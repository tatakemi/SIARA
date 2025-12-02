# views/my_posts_view.py
import flet as ft
from models import LostAnimal, FoundReport, session_scope
from services.geocoding import reverse_geocode, build_static_map_url

class MyPostsView(ft.UserControl):
    """View para listar, editar e deletar posts do usuário logado."""
    def __init__(self, page, state, show_snack, show_home):
        super().__init__()
        self.page = page
        self.state = state
        self.show_snack = show_snack
        self.show_home = show_home
        self.cur = state["current_user"]
        
        self.my_lost_list = ft.ListView(expand=True, spacing=8)
        self.my_found_list = ft.ListView(expand=True, spacing=8)
        self.main_content = ft.Column(expand=True)
        
        # O estado local para gerenciar qual post está sendo editado
        self.editing_data = None 
        self.editing_type = None 

    # --- Lógica de Carregamento ---
    def load_data(self):
        with session_scope() as s:
            losts_rows = s.query(LostAnimal).filter_by(owner_id=self.cur["id"]).order_by(LostAnimal.id.desc()).all()
            founds_rows = s.query(FoundReport).filter_by(finder_id=self.cur["id"]).order_by(FoundReport.id.desc()).all()
            
            # Converte para dicionários para evitar erros de "detached instance"
            self.losts = [{
                "id": a.id, "name": a.name, "lost_location": a.lost_location, "desc_animal": a.desc_animal,
                "latitude": a.latitude, "longitude": a.longitude, "species": a.species, "contact": a.contact
            } for a in losts_rows]

            self.founds = [{
                "id": r.id, "species": r.species, "found_location": r.found_location, "found_description": r.found_description,
                "latitude": r.latitude, "longitude": r.longitude, "found_date": r.found_date
            } for r in founds_rows]

    def build_list(self):
        self.my_lost_list.controls.clear()
        for ld in self.losts:
            info = f"{ld['name']} — {ld['lost_location'] or ''}\n{ld['desc_animal'] or ''}"
            if ld['latitude'] and ld['longitude']:
                info += f"\nCoords: {ld['latitude']:.6f}, {ld['longitude']:.6f}"
            
            item = ft.Container(
                ft.Row([
                    ft.Column([ft.Text(ld['name'], weight=ft.FontWeight.BOLD), ft.Text(info)], expand=True),
                    ft.Column([
                        ft.ElevatedButton("Editar", on_click=lambda e, aid=ld['id']: self.show_edit_form("lost", aid)),
                        ft.TextButton("Deletar", on_click=lambda e, aid=ld['id']: self.confirm_delete_lost(aid))
                    ])
                ]),
                bgcolor=ft.Colors.BLACK12, padding=12, margin=3, border_radius=8
            )
            self.my_lost_list.controls.append(item)

        self.my_found_list.controls.clear()
        for fd in self.founds:
            info = f"{fd['species'] or 'Animal encontrado'} — {fd['found_location'] or ''}\n{fd['found_description'] or ''}"
            if fd['latitude'] and fd['longitude']:
                info += f"\nCoords: {fd['latitude']:.6f}, {fd['longitude']:.6f}"
            
            item = ft.Container(
                ft.Row([
                    ft.Column([ft.Text(fd['species'] or "Animal encontrado", weight=ft.FontWeight.BOLD), ft.Text(info)], expand=True),
                    ft.Column([
                        ft.ElevatedButton("Editar", on_click=lambda e, rid=fd['id']: self.show_edit_form("found", rid)),
                        ft.TextButton("Deletar", on_click=lambda e, rid=fd['id']: self.confirm_delete_found(rid))
                    ])
                ]),
                bgcolor=ft.Colors.INDIGO_ACCENT, padding=12, margin=3, border_radius=8
            )
            self.my_found_list.controls.append(item)
            
        if not self.losts and not self.founds:
            return ft.Column([ft.Text("Você não tem posts ainda."), ft.Row([ft.ElevatedButton("Voltar", on_click=self.show_home)])])
            
        return ft.Column([
            ft.Text("Meus animais perdidos"), self.my_lost_list, 
            ft.Text("Animais que encontrei"), self.my_found_list, 
            ft.Row([ft.ElevatedButton("Voltar", on_click=self.show_home)])
        ])

    # --- Lógica de Edição ---
    def show_edit_form(self, type, post_id):
        self.editing_type = type
        self.editing_data = next((item for item in (self.losts if type == "lost" else self.founds) if item['id'] == post_id), None)
        
        if not self.editing_data:
            self.show_snack("Registro não encontrado", success=False)
            self.main_content.controls.clear()
            self.main_content.controls.append(self.build_list())
            self.update()
            return
            
        # Limpar e montar o formulário de edição
        self.main_content.controls.clear()
        self.main_content.controls.append(self.build_edit_form())
        self.update()

    def build_edit_form(self):
        # A complexa lógica do formulário de edição (LostAnimal ou FoundReport)
        data = self.editing_data
        is_lost = self.editing_type == "lost"
        
        # Campos genéricos (nome/espécie, localização, descrição, lat/lon)
        field1 = ft.TextField(label="Nome do animal" if is_lost else "Espécie (opcional)", value=data.get("name") or data.get("species") or "")
        field2 = ft.TextField(label="Local perdido" if is_lost else "Local encontrado", value=data.get("lost_location") or data.get("found_location") or "")
        field3 = ft.TextField(label="Descrição do animal", value=data.get("desc_animal") or data.get("found_description") or "")
        
        # Campos específicos
        contact_field = ft.TextField(label="Contato (opcional)", value=data.get("contact") or "") if is_lost else None
        date_field = ft.TextField(label="Data (opcional)", value=data.get("found_date") or "") if not is_lost else None
        
        lat_field = ft.TextField(label="Latitude (opcional)", value=f"{data['latitude']:.6f}" if data['latitude'] is not None else "")
        lon_field = ft.TextField(label="Longitude (opcional)", value=f"{data['longitude']:.6f}" if data['longitude'] is not None else "")
        preview_image = ft.Image(src="", width=600, height=300)
        preview_address = ft.Text("", selectable=True)
        msg = ft.Text("")
        
        def update_preview_from_fields(e=None):
            try:
                if lat_field.value.strip() and lon_field.value.strip():
                    lat = float(lat_field.value.strip()); lon = float(lon_field.value.strip())
                    preview_image.src = build_static_map_url(lat, lon)
                    preview_address.value = reverse_geocode(lat, lon) or "Endereço não encontrado"
                else:
                    preview_image.src = ""
                    preview_address.value = ""
            except Exception:
                preview_image.src = ""
                preview_address.value = ""
            
            self.update()

        def do_update(ev):
            try:
                lat = float(lat_field.value.strip()) if lat_field.value.strip() else None
                lon = float(lon_field.value.strip()) if lon_field.value.strip() else None
            except:
                msg.value = "Coordenadas inválidas"
                self.update()
                return

            with session_scope() as s:
                if is_lost:
                    obj = s.query(LostAnimal).filter_by(id=data["id"], owner_id=self.cur["id"]).first()
                    if not obj: return self.show_snack("Reg não encontrado", success=False)
                    obj.name = field1.value.strip()
                    obj.species = obj.species # manter o campo species
                    obj.lost_location = field2.value.strip() or None
                    obj.desc_animal = field3.value.strip() or None
                    obj.contact = contact_field.value.strip() or None
                else:
                    obj = s.query(FoundReport).filter_by(id=data["id"], finder_id=self.cur["id"]).first()
                    if not obj: return self.show_snack("Reg não encontrado", success=False)
                    obj.species = field1.value.strip() or None
                    obj.found_location = field2.value.strip() or None
                    obj.found_date = date_field.value.strip() or None
                    obj.found_description = field3.value.strip() or None

                obj.latitude = lat
                obj.longitude = lon
                s.add(obj)
            
            self.show_snack("Registro atualizado.")
            self.editing_data = None
            self.editing_type = None
            self.page.go("/my_posts") # Redireciona para o final (recarrega a view)
            
        # Componentes do formulário
        form_elements = [
            ft.Text(f"Editar Registro {'Perdido' if is_lost else 'Encontrado'}", size=18),
            field1, field2, field3,
        ]
        if is_lost: form_elements.append(contact_field)
        if not is_lost: form_elements.append(date_field)

        form_elements.extend([
            ft.Row([lat_field, lon_field]),
            ft.Row([
                ft.ElevatedButton("Atualizar mapa", on_click=update_preview_from_fields),
                ft.ElevatedButton("Salvar mudanças", on_click=do_update),
                ft.TextButton("Cancelar", on_click=lambda e: self.page.go("/my_posts"))
            ]),
            preview_image, preview_address, msg
        ])

        # Chamada inicial para preencher a imagem e endereço
        update_preview_from_fields()
        return ft.Column(form_elements)

    # --- Lógica de Deleção (Diálogos) ---
    def close_dialog(self):
        if getattr(self.page, "dialog", None):
            self.page.dialog.open = False
            self.page.update()

    def confirm_delete_lost(self, lost_id):
        dlg = ft.AlertDialog(
            title=ft.Text("Deletar registro de animal perdido?"),
            content=ft.Text("Esta ação não pode ser desfeita."),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.close_dialog()),
                ft.ElevatedButton("Deletar", bgcolor=ft.Colors.RED, on_click=lambda e: self.do_delete_lost(lost_id))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()
        
    def do_delete_lost(self, lost_id):
        self.close_dialog()
        try:
            with session_scope() as s:
                obj = s.get(LostAnimal, int(lost_id))
                if not obj or obj.owner_id != self.cur["id"]:
                    self.show_snack("Registro não encontrado", success=False)
                    return
                s.delete(obj)
            self.show_snack("Registro deletado.")
        except Exception as ex:
            print("Error deleting lost report:", ex)
            self.show_snack("Falha ao deletar o registro.", success=False)
        
        # Redireciona para recarregar a lista (melhor que atualizar apenas o controle)
        self.page.go("/my_posts") 

    def confirm_delete_found(self, found_id):
        dlg = ft.AlertDialog(
            title=ft.Text("Deletar registro de animal encontrado?"),
            content=ft.Text("Esta ação não pode ser desfeita."),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.close_dialog()),
                ft.ElevatedButton("Deletar", bgcolor=ft.Colors.RED, on_click=lambda e, fid=found_id: self.do_delete_found(fid))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def do_delete_found(self, found_id):
        self.close_dialog()
        try:
            with session_scope() as s:
                obj = s.get(FoundReport, int(found_id))
                if not obj or obj.finder_id != self.cur["id"]:
                    self.show_snack("Registro não encontrado", success=False)
                    return
                s.delete(obj)
            self.show_snack("Registro deletado.")
        except Exception as ex:
            print("Error deleting found report:", ex)
            self.show_snack("Falha ao deletar o registro.", success=False)

        self.page.go("/my_posts")

    # --- Renderização Principal ---
    def build(self):
        if not self.cur:
            self.show_home() 
            return ft.Container(ft.Text("Redirecionando..."))
        
        # Carregar dados e construir a lista
        self.load_data()
        self.main_content.controls.clear()
        self.main_content.controls.append(self.build_list())
        
        return ft.Column([ft.Text("Meus Posts", size=18), self.main_content], expand=True)
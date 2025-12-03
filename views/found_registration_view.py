# found_registration_view.py
import flet as ft
from models import FoundReport, session_scope 
from services.geocoding import geocode_address, reverse_geocode, build_static_map_url 
from services.map_server import LAST_PICK 

def show_found_registration(page, state, go_to_home_func, show_snack_func):
    page.controls.clear()
    cur = state.get("current_user")
    if not cur:
        go_to_home_func()
        return

    # --- 1. CARREGAR DADOS PARA EDIÇÃO (CORRIGIDO: DetachedInstanceError) ---
    edit_id = state.get("edit_found_id")
    current_post_data = None # Armazena os dados do post em um dicionário (seguro fora da sessão)

    if edit_id is not None:
        try:
            with session_scope() as s:
                # Carrega o post, garantindo que o usuário logado é o dono
                current_post_obj = s.query(FoundReport).filter_by(id=edit_id, finder_id=cur["id"]).first()
                
                if current_post_obj:
                    # **CORREÇÃO**: Converte o objeto ORM para um dicionário (dict)
                    current_post_data = {
                        'id': current_post_obj.id,
                        'species': current_post_obj.species,
                        'found_description': current_post_obj.found_description,
                        'found_location': current_post_obj.found_location,
                        'found_date': current_post_obj.found_date,
                        'latitude': current_post_obj.latitude,
                        'longitude': current_post_obj.longitude,
                    }
                else:
                    state["edit_found_id"] = None
                    show_snack_func("Relato para edição não encontrado.", is_error=True)
        except Exception as e:
            print(f"Erro ao carregar relato para edição (Found): {e}")
            current_post_data = None
            state["edit_found_id"] = None
            show_snack_func("Erro ao carregar dados.", is_error=True)


    # Função auxiliar para obter valores de forma segura (do dicionário ou string vazia)
    def get_val(key, default=''):
        return current_post_data.get(key, default) if current_post_data else default
        
    # --- 2. DEFINIÇÃO DOS CAMPOS (e pré-preenchimento) ---
    
    initial_lat_raw = get_val('latitude')
    initial_lon_raw = get_val('longitude')

    # **********************************************
    # CORREÇÃO DO ERRO: 
    # Verifica se o valor é numérico antes de formatar.
    # Se for string (ex: "") ou None, usa ""
    # **********************************************
    if isinstance(initial_lat_raw, (float, int)):
        initial_lat = f"{initial_lat_raw:.6f}"
    else:
        initial_lat = "" 
        
    if isinstance(initial_lon_raw, (float, int)):
        initial_lon = f"{initial_lon_raw:.6f}"
    else:
        initial_lon = "" 
    # **********************************************

    species = ft.TextField(label="Espécie (opcional)", value=get_val('species'))
    location = ft.TextField(label="Onde foi encontrado (endereço ou descrição)", value=get_val('found_location'))
    date = ft.TextField(label="Data (opcional)", value=get_val('found_date'))
    desc = ft.TextField(label="Descrição do animal", value=get_val('found_description'))
    
    lat_field = ft.TextField(label="Latitude (opcional)", value=initial_lat)
    lon_field = ft.TextField(label="Longitude (opcional)", value=initial_lon)
    msg = ft.Text("")

    preview_image = ft.Image(src="", width=600, height=300)
    preview_address = ft.Text("", selectable=True)
    
    title_text = "Editar Relato de Animal Encontrado" if current_post_data else "Registrar Animal Encontrado"
    button_text = "Salvar Alterações" if current_post_data else "Salvar Registro"


    # --- 3. FUNÇÕES DE ATUALIZAÇÃO E GEOCÓDIGO ---
    def update_preview_from_fields():
        try:
            current_lat = lat_field.value.strip()
            current_lon = lon_field.value.strip()
            
            if current_lat and current_lon:
                lat = float(current_lat)
                lon = float(current_lon)
                preview_image.src = build_static_map_url(lat, lon, zoom=14)
                address = reverse_geocode(lat, lon)
                preview_address.value = f"Endereço aproximado: {address or 'Não encontrado'}"
            elif location.value.strip():
                lat, lon = geocode_address(location.value)
                if lat is not None and lon is not None:
                    lat_field.value = f"{lat:.6f}"
                    lon_field.value = f"{lon:.6f}"
                    preview_image.src = build_static_map_url(lat, lon, zoom=14)
                    preview_address.value = f"Endereço geocodificado: {location.value}"
                else:
                    preview_image.src = ""
                    preview_address.value = "Não foi possível geocodificar o endereço."
            else:
                preview_image.src = ""
                preview_address.value = ""
                
            page.update()
        except ValueError:
            preview_address.value = "Erro: Latitude/Longitude inválidas."
            preview_image.src = ""
            page.update()
        except Exception as e:
            print(f"Erro em update_preview_from_fields (found): {e}")

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

    # Chama a função para carregar o preview inicial caso haja dados
    if current_post_data:
        update_preview_from_fields()

    # --- 4. FUNÇÃO DE SALVAMENTO (INSERT ou UPDATE) ---
    def do_register_found(ev):
        desc_val = desc.value.strip()
        location_val = location.value.strip()
        lat_val = lat_field.value.strip()
        lon_val = lon_field.value.strip()
        
        if not desc_val:
            msg.value = "A descrição do animal é obrigatória."
            page.update()
            return

        # Geocodificação se for só endereço
        if location_val and not (lat_val and lon_val):
            lat, lon = geocode_address(location_val)
            if lat is None or lon is None:
                msg.value = "Não foi possível encontrar as coordenadas para o endereço fornecido. Tente usar o mapa."
                page.update()
                return
            lat_val = f"{lat:.6f}"
            lon_val = f"{lon:.6f}"

        try:
            with session_scope() as s:
                post_to_save = None
                
                if current_post_data: 
                    # **MODO EDIÇÃO**: Busca o objeto novamente DENTRO da nova sessão para UPDATE
                    post_to_save = s.query(FoundReport).filter_by(id=current_post_data['id'], finder_id=cur["id"]).first()
                    
                if post_to_save is None:
                    # **MODO CRIAÇÃO (ou se a busca do post falhou)**
                    post_to_save = FoundReport(finder_id=cur["id"])
                    s.add(post_to_save) 
                    
                # **MODO CRIAÇÃO OU EDIÇÃO: ATUALIZAÇÃO DE CAMPOS**
                post_to_save.species = species.value.strip()
                post_to_save.found_description = desc_val
                post_to_save.found_location = location_val
                post_to_save.found_date = date.value.strip()
                
                # Coordenadas
                post_to_save.latitude = float(lat_val) if lat_val else None
                post_to_save.longitude = float(lon_val) if lon_val else None

            # Resetar o estado de edição após salvar
            is_edit_mode = state.get("edit_found_id") is not None
            if is_edit_mode:
                state["edit_found_id"] = None
                show_snack_func("Relato de animal encontrado atualizado com sucesso!")
                go_to_home_func() # Volta para a home ou my_posts
            else:
                show_snack_func("Registro de animal encontrado salvo.")
                # Limpa campos para novo registro
                species.value = location.value = date.value = desc.value = ""
                lat_field.value = lon_field.value = ""
                update_preview_from_fields()
                
        except Exception as e:
            print(f"Erro ao salvar relato (Found): {e}")
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
            ft.ElevatedButton(button_text, on_click=do_register_found,
                              style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700 if current_post_data else ft.Colors.BLUE_700, color=ft.Colors.WHITE)),
            ft.TextButton("Voltar", on_click=go_to_home_func)
        ]),
        preview_image,
        preview_address,
        msg
    )
    page.update()
import flet as ft
import flet_map as fmap
from math import radians, sin, cos, sqrt, atan2
from models import session_scope


# distância em metros entre duas coordenadas
def distance_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (sin(dlat / 2) ** 2 +
         cos(radians(lat1)) * cos(radians(lat2)) *
         sin(dlon / 2) ** 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def show_map(page: ft.Page, state: dict, route_logics: dict):
    """
    page: flet page
    state: estado compartilhado (dicionário)
    route_logics: dicionário de rotas (mesma estrutura que você já passa)
    """

    page.controls.clear()

    # reset da coordenada selecionada (se quiser preservar comentário essa linha)
    state["picked_coords"] = state.get("picked_coords", None)

    # ---------------------------------------------------------
    # 1) ler e serializar tudo o que precisamos do banco (dentro da sessão)
    #    para evitar DetachedInstanceError
    # ---------------------------------------------------------
    lost_rows = []
    found_rows = []
    with session_scope() as s:
        # só puxar os campos primários que usaremos
        for r in s.query(__import__("models").LostAnimal).all():
            lost_rows.append({
                "id": r.id,
                "name": getattr(r, "name", None),
                "species": getattr(r, "species", None),
                "desc": getattr(r, "desc_animal", None),
                "lat": float(r.latitude) if r.latitude is not None else None,
                "lon": float(r.longitude) if r.longitude is not None else None,
            })
        for r in s.query(__import__("models").FoundReport).all():
            found_rows.append({
                "id": r.id,
                "species": getattr(r, "species", None),
                "desc": getattr(r, "found_description", None),
                "lat": float(r.latitude) if r.latitude is not None else None,
                "lon": float(r.longitude) if r.longitude is not None else None,
            })

    # ---------------------------------------------------------
    # 2) construir marcadores (sempre novos — evita duplicação)
    #    cada Marker tem `content` que é um controle Flet com on_click
    # ---------------------------------------------------------
    markers = []

    def make_icon_container(icon, color, size=26):
        return ft.Container(
            content=ft.Icon(icon, color=color, size=size),
            padding=2,
            on_click=None,  # será setado por closure ao criar o marker
            tooltip=None,
            width=size + 8,
            height=size + 8,
        )

    # lista de objetos para usar na detecção por distância (clicar em marcador)
    marker_info_list = []

    for item in lost_rows:
        if item["lat"] is None or item["lon"] is None:
            continue
        info = {
            "type": "lost",
            "id": item["id"],
            "name": item["name"],
            "species": item["species"],
            "desc": item["desc"],
            "lat": item["lat"],
            "lon": item["lon"],
        }
        # cria container e associa on_click
        container = make_icon_container(ft.Icons.PETS, ft.Colors.RED, size=26)

        # handler local (closure) para abrir popup com as informações
        def make_click_handler(info):
            def _on_click(e: ft.ControlEvent):
                open_info_popup(info)
            return _on_click

        container.on_click = make_click_handler(info)

        # cria Marker do flet_map
        markers.append(
            fmap.Marker(
                content=container,
                coordinates=fmap.MapLatitudeLongitude(info["lat"], info["lon"])
            )
        )

        marker_info_list.append(info)

    for item in found_rows:
        if item["lat"] is None or item["lon"] is None:
            continue
        info = {
            "type": "found",
            "id": item["id"],
            "name": None,
            "species": item["species"],
            "desc": item["desc"],
            "lat": item["lat"],
            "lon": item["lon"],
        }
        container = make_icon_container(ft.Icons.LOCATION_ON, ft.Colors.GREEN, size=26)
        def make_click_handler(info):
            def _on_click(e: ft.ControlEvent):
                open_info_popup(info)
            return _on_click
        container.on_click = make_click_handler(info)

        markers.append(
            fmap.Marker(
                content=container,
                coordinates=fmap.MapLatitudeLongitude(info["lat"], info["lon"])
            )
        )
        marker_info_list.append(info)

    # ---------------------------------------------------------
    # 3) função que abre um AlertDialog com os detalhes do item
    # ---------------------------------------------------------
    def open_info_popup(info: dict):
        # monta colunas com os campos que temos
        rows = []
        rows.append(ft.Text(f"Tipo: {'Perdido' if info['type']=='lost' else 'Encontrado'}"))
        if info.get("name"):
            rows.append(ft.Text(f"Nome: {info['name']}"))
        rows.append(ft.Text(f"Espécie: {info.get('species', '—')}"))
        rows.append(ft.Text(f"Descrição: {info.get('desc', '—')}"))

        # ação de "ver post completo" — tenta usar route_logics se existir
        def on_view_full(e):
            # fecha o popup primeiro
            page.dialog.open = False
            page.update()
            # se você tiver uma rota para posts (ex: 'lost_post' / 'found_post'), chame-a
            # aqui estamos seguindo sua convenção de rotas: route_logics é um dicionário.
            # caso não exista rota, apenas mostra um aviso.
            if info["type"] == "lost":
                # exemplo: setar estado e tentar chamar rota (descomente se tiver rota)
                state["view_lost_post_id"] = info["id"]
                if "view_lost_post" in route_logics:
                    route_logics["view_lost_post"]()
                    return
            else:
                state["view_found_post_id"] = info["id"]
                if "view_found_post" in route_logics:
                    route_logics["view_found_post"]()
                    return

            # rota não existe: avisar
            page.snack_bar = ft.SnackBar(ft.Text("Nenhuma view de post configurada."), bgcolor=ft.Colors.BLUE_600)
            page.snack_bar.open = True
            page.update()

        def on_close(e=None):
            page.dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Informações do animal"),
            content=ft.Column(rows, tight=True),
            actions=[
                ft.TextButton("Ver post completo", on_click=on_view_full),
                ft.TextButton("Fechar", on_click=on_close),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.dialog = dialog
        dialog.open = True
        page.update()

    # ---------------------------------------------------------
    # 4) evento de clique no mapa (tap) — detecta clique em marcador por proximidade
    # ---------------------------------------------------------
    def handle_map_tap(e: fmap.MapTapEvent):
        # coordenada selecionada
        lat = e.coordinates.latitude
        lon = e.coordinates.longitude

        # salva seleção para o form (ao voltar)
        state["picked_coords"] = (lat, lon)

        # tenta detectar clique em marcador (proximidade em metros)
        for mk in marker_info_list:
            d = distance_m(lat, lon, mk["lat"], mk["lon"])
            if d < 20:  # threshold (m) — ajuste se quiser
                open_info_popup(mk)
                return

        # se não foi marcador, apenas mostra snack com coords
        page.snack_bar = ft.SnackBar(ft.Text(f"Coordenada selecionada: {lat:.6f}, {lon:.6f}"))
        page.snack_bar.open = True
        page.update()

    # ---------------------------------------------------------
    # 5) camadas e mapa
    # ---------------------------------------------------------
    tile_layer = fmap.TileLayer(url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png")
    marker_layer = fmap.MarkerLayer(markers=markers)
    m = fmap.Map(
        layers=[tile_layer, marker_layer],
        initial_center=fmap.MapLatitudeLongitude(-25.4284, -49.2733),
        initial_zoom=13,
        expand=True,
        on_tap=handle_map_tap,
    )

    # ---------------------------------------------------------
    # 6) layout e botão voltar (usa route_logics para voltar à view correta)
    # ---------------------------------------------------------
    page.add(
        ft.Text("Mapa - toque para selecionar localização", size=20, weight=ft.FontWeight.BOLD),
        ft.Container(height=12),
        m,
        ft.Container(height=20),
        ft.Row(
            [
                ft.ElevatedButton(
                    "Voltar",
                    on_click=lambda e: route_logics.get(state.get("return_to", "home"), lambda: None)()
                )
            ],
            alignment=ft.MainAxisAlignment.END
        ),
    )

    page.update()

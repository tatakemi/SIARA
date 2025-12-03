# home_view.py
import flet as ft
from models import LostAnimal, FoundReport, session_scope 
# Importa a função do arquivo 'my_posts_view.py' para reutilização
from views.my_posts_view import build_post_card 

# A assinatura AGORA tem 8 argumentos
def show_home(page, state, go_to_login_func, go_to_lost_reg_func, go_to_found_reg_func, go_to_my_posts_func, go_to_map_func, do_logout_func):
    page.controls.clear()
    cur = state.get("current_user")
    
    # 1. Se não houver usuário logado, retorna para o login
    if not cur:
        go_to_login_func() 
        return

    # 2. Definição do cabeçalho com o botão de Logout
    header = ft.Row([
        ft.Text(f"Bem-vindo, {cur['username']}!", size=24, weight=ft.FontWeight.BOLD),
        ft.ElevatedButton("Logout", on_click=do_logout_func, 
                          style=ft.ButtonStyle(bgcolor=ft.Colors.RED_400, color=ft.Colors.WHITE))
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    
    # 3. Definição dos botões de navegação
    navigation_buttons = ft.Row(
        [
            ft.ElevatedButton("Cadastrar Animal Perdido", on_click=go_to_lost_reg_func),
            ft.ElevatedButton("Relatar Animal Encontrado", on_click=go_to_found_reg_func),
            ft.ElevatedButton("Meus Posts", on_click=go_to_my_posts_func),
            ft.ElevatedButton("Ver Mapa", on_click=go_to_map_func),
        ],
        wrap=True,
        alignment=ft.MainAxisAlignment.CENTER
    )

    # --- 4. NOVO: Carregamento e Exibição dos Posts ---
    all_posts = []
    
    try:
        with session_scope() as s:
            # Busca todos os posts, ordenados por ID para ter os mais recentes primeiro
            lost_animals = s.query(LostAnimal).order_by(LostAnimal.id.desc()).all()
            found_reports = s.query(FoundReport).order_by(FoundReport.id.desc()).all()

            # Cria os cards de posts para animais perdidos
            for animal in lost_animals:
                # Passamos None para os handlers, pois a Home não deve ter botões de Edição/Exclusão
                card = build_post_card(
                    title=f"🚨 PERDIDO: {animal.species or 'Animal'} - {animal.name or 'Sem nome'}", 
                    location_text=animal.lost_location, 
                    description=animal.desc_animal, 
                    lat=animal.latitude, 
                    lon=animal.longitude, 
                    is_lost=True, 
                    item_id=animal.id,
                    on_edit_click=None,
                    on_delete_click=None
                )
                all_posts.append(card)

            # Cria os cards de posts para relatos de encontrados
            for report in found_reports:
                card = build_post_card(
                    title=f"✅ ENCONTRADO: {report.species or 'Animal'}", 
                    location_text=report.found_location, 
                    description=report.found_description, 
                    lat=report.latitude, 
                    lon=report.longitude, 
                    is_lost=False, 
                    item_id=report.id,
                    on_edit_click=None,
                    on_delete_click=None
                )
                all_posts.append(card)
                
    except Exception as e:
        print(f"Erro ao carregar todos os posts: {e}")
        all_posts.append(ft.Text(f"Erro ao carregar posts: {e}", color=ft.Colors.RED))
        
    # Container/ListView para os posts com rolagem
    posts_list_view = ft.ListView(
        controls=all_posts if all_posts else [ft.Text("Nenhum registro encontrado no sistema.")], 
        spacing=10, 
        expand=True,
        auto_scroll=False,
        padding=ft.padding.only(top=10, bottom=10)
    )

    # 5. Adição dos controles à página
    page.add(
        header,
        ft.Divider(),
        navigation_buttons,
        ft.Text("Últimos Registros de Animais (Perdidos e Encontrados):", size=18, weight=ft.FontWeight.BOLD),
        posts_list_view, 
        ft.Text("Use o menu de navegação para interagir com o sistema.")
    )

    page.update()
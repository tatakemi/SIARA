import flet as ft

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
        # Usa o novo argumento 'do_logout_func'
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

    # 4. Adição dos controles à página
    page.add(
        header,
        ft.Divider(),
        navigation_buttons,
        ft.Text("Use o menu acima para gerenciar seus posts e o mapa para ver posts de outros usuários.", 
                size=14, color=ft.Colors.BLACK54)
    )
    page.update()

# Garante que a função exportada é show_home
# show_home é a própria função, mas definida por convenção
# Se o seu arquivo só tiver 'show_home', você pode remover esta linha
# show_home = show_home
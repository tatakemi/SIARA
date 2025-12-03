# map_server.py
import os
import threading
import socket
import json
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path

# ************************************************************
# 1. IMPORTAÇÕES E CONFIGURAÇÃO INICIAL
# ************************************************************

# Você precisará importar a lógica de banco de dados
from models import LostAnimal, FoundReport, session_scope 

# Variáveis globais e utilitários
STATIC_DIR = Path(os.getcwd()) / "map_static"
STATIC_DIR.mkdir(exist_ok=True) # Cria a pasta se não existir (onde fica map.html)

LAST_PICK = {"lat": None, "lon": None}   # Armazena a última coordenada clicada no mapa

_httpd = None
_httpd_thread = None

def find_free_port():
    """Encontra uma porta livre para o servidor de mapa."""
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

# ************************************************************
# 2. CLASSE MapHandler (Lida com requisições HTTP)
# ************************************************************
class MapHandler(SimpleHTTPRequestHandler):
    
    def do_GET(self):
        """Lida com requisições GET, incluindo a geração dinâmica do reports.json."""
        
        # Lógica para o endpoint reports.json (dados dos pins)
        if self.path.startswith("/reports.json"):
            try:
                reports = []
                with session_scope() as s:
                    
                    # Carrega Animais Perdidos
                    for a in s.query(LostAnimal).all():
                        if a.latitude is not None and a.longitude is not None:
                            reports.append({
                                # NOVO: Usa o tipo simplificado 'lost' para o JavaScript
                                "type": "lost", 
                                "title": f"Perdido: {a.name or 'Sem nome'}",
                                "desc": f"Descrição: {a.desc_animal or 'N/A'}<br>Local: {a.lost_location or 'Não informado'}",
                                "lat": a.latitude,
                                "lon": a.longitude
                            })

                    # Carrega Relatos de Encontrados
                    for r in s.query(FoundReport).all():
                        if r.latitude is not None and r.longitude is not None:
                            reports.append({
                                # NOVO: Usa o tipo simplificado 'found' para o JavaScript
                                "type": "found",
                                "title": f"Encontrado: {r.species or 'Animal'}",
                                "desc": f"Descrição: {r.found_description or 'N/A'}<br>Local: {r.found_location or 'Não informado'}",
                                "lat": r.latitude,
                                "lon": r.longitude
                            })
                
                # Responde com o JSON
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(reports).encode('utf-8'))
                
            except Exception as e:
                print(f"Erro ao servir reports.json: {e}")
                self.send_error(500)
        else:
            # Para todos os outros arquivos (map.html, leaflet.css, etc.)
            return super().do_GET()

    def do_POST(self):
        """Lida com requisições POST, especificamente para receber coordenadas."""
        
        # Lógica para o endpoint /pick (coordenada clicada)
        if self.path.startswith("/pick"):
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
            
            # Atualiza a variável global LAST_PICK
            LAST_PICK["lat"] = payload.get("lat")
            LAST_PICK["lon"] = payload.get("lon")
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_error(404)

# ************************************************************
# 3. FUNÇÕES DE CONTROLE DO SERVIDOR
# ************************************************************

def start_map_server(port):
    """Inicia o servidor HTTP em uma thread separada."""
    global _httpd, _httpd_thread
    if _httpd is None:
        # Configura o handler para servir arquivos estáticos do STATIC_DIR
        Handler = partial(MapHandler, directory=str(STATIC_DIR))
        _httpd = HTTPServer(("", port), Handler)
        _httpd_thread = threading.Thread(target=_httpd.serve_forever, daemon=True)
        _httpd_thread.start()
        print(f"Servidor de mapa iniciado na porta {port}")

def stop_map_server():
    """Para o servidor HTTP."""
    global _httpd
    if _httpd:
        print("Parando servidor de mapa...")
        # Usa threading.Thread para garantir que o shutdown não bloqueie o Flet
        threading.Thread(target=_httpd.shutdown).start() 
        _httpd = None

def write_base_map_html():
    """
    Cria ou sobrescreve o arquivo map.html na pasta estática.
    Isso deve ser chamado no app.py na inicialização.
    """
    html_content = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" integrity="sha512-DTOQO9RWCH3ppGqcWaEA1BIZOC6xxalwEsw9c2QQeAIftl+Vegovlnee1c9QX4TctnWMn13TZye+giMm8e2LwA==" crossorigin="anonymous" referrerpolicy="no-referrer" />
<style>
    html,body,#map{{height:100%;margin:0;padding:0}}

    /* Estilo para o ícone de Lost (Perdido) - Red X */
    .lost-icon-div {{
        background-color: white;
        border: 2px solid red;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        line-height: 26px; /* Alinhamento vertical do texto */
        text-align: center;
        box-shadow: 0 0 5px rgba(0,0,0,0.5);
    }}
    .lost-icon-div i {{
        color: red;
        font-size: 18px; 
        font-weight: bold;
    }}
    
    /* Estilo para o ícone de Found (Encontrado) - Green Check */
    .found-icon-div {{
        background-color: white;
        border: 2px solid green;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        line-height: 26px;
        text-align: center;
        box-shadow: 0 0 5px rgba(0,0,0,0.5);
    }}
    .found-icon-div i {{
        color: green;
        font-size: 18px; 
    }}

</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<script>
async function loadReports() {{
    try {{
        const res = await fetch('/reports.json');
        return await res.json();
    }} catch (e) {{
        console.error('Falha ao carregar relatórios', e);
        return [];
    }}
}}

function buildMap(reports) {{
    var map = L.map('map').setView([0,0], 2);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors'
    }}).addTo(map);

    var group = L.featureGroup();
    
    // Define os ícones personalizados (DivIcon)
    const lostIcon = L.divIcon({{
        className: 'lost-icon',
        html: '<div class="lost-icon-div"><i class="fa-solid fa-times"></i></div>', // X vermelho para perdido
        iconSize: [30, 30],
        iconAnchor: [15, 30], 
        popupAnchor: [0, -20]
    }});
    
    const foundIcon = L.divIcon({{
        className: 'found-icon',
        html: '<div class="found-icon-div"><i class="fa-solid fa-check"></i></div>', // Check verde para encontrado
        iconSize: [30, 30],
        iconAnchor: [15, 30],
        popupAnchor: [0, -20]
    }});

    reports.forEach(r=>{{
        if (!r.lat || !r.lon) return;

        let icon;
        if (r.type === 'lost') {{
            icon = lostIcon;
        }} else if (r.type === 'found') {{
            icon = foundIcon;
        }} else {{
            icon = L.icon.Default();
        }}
        
        var marker = L.marker([r.lat, r.lon], {{icon: icon}})
            .bindPopup(`<b>${{r.title || ''}}</b><br>${{r.desc || ''}}`);
            
        group.addLayer(marker);
    }});

    group.addTo(map);
    if (group.getLayers().length > 0) {{
        map.fitBounds(group.getBounds().pad(0.2));
    }}

    map.on('click', async function(e) {{
        const lat = e.latlng.lat, lon = e.latlng.lng;
        const payload = {{lat: lat, lon: lon}};
        try {{
            await fetch('/pick', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(payload)
            }});
            alert(`Coordenadas selecionadas: ${{lat.toFixed(6)}}, ${{lon.toFixed(6)}}\\nRetorne ao aplicativo e pressione "Importar coordenadas do mapa" para usá-las.`);
        }} catch (err) {{
            console.error('Erro ao enviar requisição pick:', err);
            alert('Falha ao enviar as coordenadas. Verifique a conexão do servidor.');
        }}
    }});
}}

loadReports().then(buildMap);
</script>
</body>
</html>
    """
    try:
        (STATIC_DIR / "map.html").write_text(html_content, encoding="utf-8")
        print("Arquivo map.html reescrito com sucesso na pasta map_static.")
    except Exception as e:
        print(f"Erro ao escrever map.html: {e}")
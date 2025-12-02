import os
import threading
import socket
import json
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path

# Você precisará importar a lógica de banco de dados para a função MapHandler.
from models import LostAnimal, FoundReport, session_scope 

# ---- Map server globals and utilities ----
STATIC_DIR = Path(os.getcwd()) / "map_static"
STATIC_DIR.mkdir(exist_ok=True)

LAST_PICK = {"lat": None, "lon": None}   # updated by POST /pick

_httpd = None
_httpd_thread = None

def find_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

# ---- MapHandler Class ----
class MapHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/reports.json"):
            try:
                reports = []
                with session_scope() as s:
                    # Lógica para carregar LostAnimal e FoundReport do DB
                    # ... (Seu código original aqui) ...
                    for a in s.query(LostAnimal).all():
                        reports.append({
                            "type": "Animal perdido",
                            "title": a.name,
                            "desc": f"{a.desc_animal or ''} ({a.lost_location or ''})",
                            "lat": a.latitude,
                            "lon": a.longitude
                        })
                    for r in s.query(FoundReport).all():
                        reports.append({
                            "type": "found",
                            "title": r.species or "Animal encontrado",
                            "desc": f"{r.found_description or ''} ({r.found_location or ''})",
                            "lat": r.latitude,
                            "lon": r.longitude
                        })
                
                data = json.dumps(reports).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
            return
        else:
            return super().do_GET()

    def do_POST(self):
        global LAST_PICK
        if self.path == "/pick":
            # Lógica para receber as coordenadas POST
            # ... (Seu código original aqui) ...
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body.decode('utf-8'))
                lat = payload.get("lat")
                lon = payload.get("lon")
                if lat is not None and lon is not None:
                    LAST_PICK["lat"] = float(lat)
                    LAST_PICK["lon"] = float(lon)
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"OK")
                    return
                else:
                    raise ValueError("lat/lon missing")
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
                return
        else:
            self.send_response(404)
            self.end_headers()
            return

# ---- Server Control Functions ----
def start_map_server(port):
    global _httpd, _httpd_thread
    if _httpd is not None:
        return
    handler_class = partial(MapHandler, directory=str(STATIC_DIR))
    _httpd = HTTPServer(("127.0.0.1", port), handler_class)
    def serve():
        try:
            _httpd.serve_forever()
        except Exception as e:
            print("Map server stopped:", e)
    _httpd_thread = threading.Thread(target=serve, daemon=True)
    _httpd_thread.start()
    print(f"Map server started at http://127.0.0.1:{port}/")

def stop_map_server():
    global _httpd
    if _httpd:
        _httpd.shutdown()
        _httpd = None

# ---- HTML Content ----
MAP_HTML = """<!doctype html>
... (Seu HTML/Leaflet completo aqui) ...
"""

def write_base_map_html():
    p = STATIC_DIR / "map.html"
    p.write_text(MAP_HTML, encoding="utf-8")
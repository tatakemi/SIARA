import time
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# ---- 1. Inicialização e Configuração ----

# Configuração do Geocodificador
geolocator = Nominatim(user_agent="siara_app_geocoder")

# Aplicação de limites de taxa para evitar banimento pelo serviço do Nominatim
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, return_value_on_exception=None)
reverse_rate_limited = RateLimiter(geolocator.reverse, min_delay_seconds=1, return_value_on_exception=None)

# Pequenos caches em memória (Dicionários)
_geocode_cache = {}
_reverse_cache = {}

# ---- 2. Funções de Geocodificação ----

def geocode_address(text):
    if not text:
        return None, None
    key = text.strip().lower()
    if key in _geocode_cache:
        return _geocode_cache[key]
    try:
        loc = geocode(text, timeout=10)
        if loc:
            coords = (loc.latitude, loc.longitude)
            _geocode_cache[key] = coords
            return coords
    except Exception as e:
        print("Geocode error:", e)
    _geocode_cache[key] = (None, None)
    return None, None

def reverse_geocode(lat, lon):
    if lat is None or lon is None:
        return None
    key = f"{lat:.6f},{lon:.6f}"
    if key in _reverse_cache:
        return _reverse_cache[key]
    try:
        loc = reverse_rate_limited(f"{lat}, {lon}", exactly_one=True, timeout=10)
        if loc and getattr(loc, "address", None):
            address = loc.address
            _reverse_cache[key] = address
            return address
    except Exception as e:
        print("Reverse geocode error:", e)
    _reverse_cache[key] = None
    return None

# ---- 3. Funções Auxiliares ----

def build_static_map_url(lat, lon, zoom=15, width=600, height=300, marker="red-pushpin"):
    if lat is None or lon is None:
        return ""
    ts = int(time.time() * 1000)  # cache buster to force fresh image
    url = f"https://staticmap.openstreetmap.de/staticmap.php?center={lat},{lon}&zoom={zoom}&size={width}x{height}&markers={lat},{lon},{marker}&ts={ts}"
    # Não vamos incluir o print aqui no módulo de serviço.
    return url
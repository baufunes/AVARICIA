"""
Configuración central del proyecto.
Carga la API key desde el archivo .env (nunca hardcodeamos keys en el código).
"""
import os
from dotenv import load_dotenv
from src.paths import path as resolve_path

# Busca el archivo .env (en la carpeta del proyecto, o al lado del .app si
# está empaquetado) y carga las variables
load_dotenv(resolve_path(".env"))

FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"

# API-Football (api-sports.io) - para córners, tarjetas y árbitros.
# Se consigue gratis en https://dashboard.api-football.com/register
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
API_FOOTBALL_SEASON = 2026
# Nombre de liga que usa API-Football para el Mundial (a confirmar la
# primera vez que corras el proyecto - ver README).
API_FOOTBALL_WC_LEAGUE_NAME = "World Cup"

# API-Football (api-sports.io) — para córners, tarjetas y árbitros.
# No pude confirmar en vivo el ID de liga exacto para el Mundial 2026 en
# esta API (mi entorno no tiene acceso a internet); si las estadísticas no
# aparecen, revisá con GET /leagues?name=World Cup en la doc de api-sports.io
# y ajustá API_FOOTBALL_WC_LEAGUE_ID.
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
API_FOOTBALL_WC_LEAGUE_ID = 1
API_FOOTBALL_SEASON = 2026

# Código de competición del Mundial en football-data.org
WORLD_CUP_CODE = "WC"

# Rating Elo inicial para un equipo del que no tenemos historial
DEFAULT_ELO = 1500

# K-factor: qué tan rápido se mueve el Elo con cada resultado.
# Usamos K más alto para partidos de Mundial (pesan más) que para amistosos.
K_FACTOR_BY_TOURNAMENT = {
    "FIFA World Cup": 60,
    "FIFA World Cup qualification": 40,
    "friendly": 20,
    "default": 30,
}

# Cuántas simulaciones Monte Carlo corremos por partido
N_SIMULATIONS = 20000

if not FOOTBALL_DATA_API_KEY:
    print(
        "⚠️  No encontré FOOTBALL_DATA_API_KEY en tu archivo .env.\n"
        "   Copiá .env.example como .env y pegá tu key ahí antes de correr el proyecto."
    )

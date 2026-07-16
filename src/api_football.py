"""
Conexión con API-Football (api-sports.io) para traer córners, tarjetas y
árbitros. A diferencia de football-data.org, esta API sí tiene estadísticas
de partido detalladas.

IMPORTANTE sobre el uso de requests: el plan gratuito tiene 100 requests/día.
Para no desperdiciarlos, todo acá se cachea en disco (data/api_football_cache.json)
- si ya trajiste las estadísticas de un partido, no se vuelven a pedir.

Además, deliberadamente limitamos el historial a los partidos DE ESTE MISMO
MUNDIAL (no toda la carrera del equipo/árbitro), para mantener pocas
requests y porque la forma reciente es lo más relevante para predecir. Es
una muestra chica, tomalo como aproximación, no como dato definitivo.

NOTA: no pude probar esta API en vivo desde mi entorno (sin acceso a
internet). Los nombres de endpoints y parámetros están basados en la
documentación de API-Football v3, pero si algo cambió avisame el error
exacto y lo ajustamos. Doc oficial: https://www.api-football.com/documentation-v3
"""
import json
import os
import time
import requests
from src.config import (
    API_FOOTBALL_KEY,
    API_FOOTBALL_BASE_URL,
    API_FOOTBALL_SEASON,
    API_FOOTBALL_WC_LEAGUE_NAME,
)

from src.paths import path as resolve_path

CACHE_PATH = resolve_path("data", "api_football_cache.json")
MANUAL_REFEREES_PATH = resolve_path("data", "manual_referees.json")


def get_manual_referee(team_a: str, team_b: str):
    """
    Revisa data/manual_referees.json por si el usuario cargó a mano el
    árbitro de este cruce (útil cuando ya se sabe por prensa/FIFA pero la
    API todavía no lo actualizó). Devuelve el nombre o None si no hay
    override cargado para este partido.
    """
    if not os.path.exists(MANUAL_REFEREES_PATH):
        return None

    with open(MANUAL_REFEREES_PATH, "r") as f:
        overrides = json.load(f)

    for key, referee_name in overrides.items():
        if key.startswith("_"):  # saltea el campo de comentario
            continue
        teams_in_key = set(key.split("|"))
        if teams_in_key == {team_a, team_b}:
            return referee_name

    return None


def _headers():
    return {"x-apisports-key": API_FOOTBALL_KEY}


def _load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def _get(endpoint: str, params: dict) -> dict:
    """
    Wrapper de requests.get con caché en disco: la clave de caché es el
    endpoint + los parámetros, así la misma consulta nunca se repite entre
    corridas distintas del programa (importante por el límite diario).
    """
    if not API_FOOTBALL_KEY:
        raise RuntimeError(
            "Falta API_FOOTBALL_KEY en tu .env. Registrate gratis en "
            "https://dashboard.api-football.com/register"
        )

    cache = _load_cache()
    cache_key = f"{endpoint}?{json.dumps(params, sort_keys=True)}"
    if cache_key in cache:
        return cache[cache_key]

    url = f"{API_FOOTBALL_BASE_URL}/{endpoint}"
    response = requests.get(url, headers=_headers(), params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    cache[cache_key] = data
    _save_cache(cache)
    time.sleep(0.3)  # pequeño respiro entre requests, buena práctica con APIs gratuitas

    return data


def find_world_cup_league_id() -> int:
    """Busca el ID interno que usa API-Football para el Mundial 2026."""
    data = _get("leagues", {"name": API_FOOTBALL_WC_LEAGUE_NAME})
    responses = data.get("response", [])
    for item in responses:
        league = item.get("league", {})
        if league.get("type") == "Cup" and "world cup" in league.get("name", "").lower():
            return league["id"]
    if responses:
        return responses[0]["league"]["id"]
    raise RuntimeError(
        "No pude identificar el ID de liga del Mundial en API-Football. "
        "Revisá manualmente en la doc o pedime que lo ajustemos."
    )


def find_team_id(team_name: str) -> int:
    data = _get("teams", {"name": team_name})
    responses = data.get("response", [])
    if not responses:
        raise RuntimeError(f"No encontré el equipo '{team_name}' en API-Football.")
    return responses[0]["team"]["id"]


def fetch_team_world_cup_fixtures(team_name: str, league_id: int) -> list:
    """
    Trae los partidos YA JUGADOS de este equipo en el Mundial actual.
    Devuelve una lista de dicts con: fixture_id, opponent, referee.
    """
    team_id = find_team_id(team_name)
    data = _get("fixtures", {"team": team_id, "league": league_id, "season": API_FOOTBALL_SEASON})

    fixtures = []
    for item in data.get("response", []):
        fixture = item["fixture"]
        if fixture["status"]["short"] != "FT":  # solo partidos finalizados
            continue
        teams = item["teams"]
        opponent = teams["away"]["name"] if teams["home"]["name"] == team_name else teams["home"]["name"]
        fixtures.append({
            "fixture_id": fixture["id"],
            "opponent": opponent,
            "referee": fixture.get("referee"),
        })
    return fixtures


def fetch_fixture_statistics(fixture_id: int) -> dict:
    """
    Trae córners y tarjetas de un partido específico ya jugado.
    Devuelve un dict keyed por NOMBRE DE EQUIPO (no "home"/"away"):
        {"Argentina": {"corners": int, "yellow_cards": int, "red_cards": int}, "Suiza": {...}}
    """
    data = _get("fixtures/statistics", {"fixture": fixture_id})
    result = {}
    for team_stats in data.get("response", []):
        team_name = team_stats.get("team", {}).get("name", f"equipo_{len(result)}")
        stats_by_type = {s["type"]: s["value"] for s in team_stats.get("statistics", [])}
        result[team_name] = {
            "corners": stats_by_type.get("Corner Kicks") or 0,
            "yellow_cards": stats_by_type.get("Yellow Cards") or 0,
            "red_cards": stats_by_type.get("Red Cards") or 0,
        }
    return result


def fetch_all_world_cup_fixtures(league_id: int) -> list:
    """
    Trae TODOS los partidos del Mundial actual en una sola request. La API
    no permite filtrar directamente "partidos de tal árbitro", así que esta
    es la forma de conseguir esa info: traemos todo una vez (cacheado) y
    filtramos nosotros del lado de Python.
    """
    data = _get("fixtures", {"league": league_id, "season": API_FOOTBALL_SEASON})
    fixtures = []
    for item in data.get("response", []):
        fixture = item["fixture"]
        teams = item["teams"]
        fixtures.append({
            "fixture_id": fixture["id"],
            "referee": fixture.get("referee"),
            "status": fixture["status"]["short"],
            "home": teams["home"]["name"],
            "away": teams["away"]["name"],
        })
    return fixtures


def fetch_referee_past_fixtures(referee_name: str, league_id: int) -> list:
    """
    Filtra, de todos los partidos del Mundial, los que dirigió este árbitro
    y ya están finalizados, y trae sus estadísticas (córners/tarjetas).
    """
    all_fixtures = fetch_all_world_cup_fixtures(league_id)

    referee_fixtures = [
        f for f in all_fixtures
        if f["status"] == "FT" and f["referee"] and referee_name.lower() in f["referee"].lower()
    ]

    stats_list = []
    for f in referee_fixtures:
        try:
            stats_list.append(fetch_fixture_statistics(f["fixture_id"]))
        except Exception:
            continue  # si un partido puntual falla, seguimos con los demás

    return stats_list


def find_upcoming_fixture_referee(team_a: str, team_b: str, league_id: int) -> str:
    """
    Busca el partido programado entre dos equipos y devuelve el nombre del
    árbitro asignado, si ya está definido (a veces se confirma pocos días
    antes del partido; puede devolver None).
    """
    team_id = find_team_id(team_a)
    data = _get("fixtures", {"team": team_id, "league": league_id, "season": API_FOOTBALL_SEASON})

    for item in data.get("response", []):
        teams = item["teams"]
        names = {teams["home"]["name"], teams["away"]["name"]}
        if team_a in names and team_b in names:
            return item["fixture"].get("referee")
    return None

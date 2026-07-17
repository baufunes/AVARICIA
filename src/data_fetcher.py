"""
Dos fuentes de datos:

1. load_historical_data(): lee el CSV histórico de partidos internacionales
   (lo bajás una vez de Kaggle y lo dejás en data/historical_matches.csv).
   Esto calibra Elo y las fuerzas de ataque/defensa.

2. fetch_remaining_world_cup_matches(): pega contra la API de
   football-data.org para traer los partidos del Mundial 2026 que todavía
   no se jugaron (cuartos, semis, tercer puesto, final).

NOTA: no pude probar esta API en vivo desde mi entorno (sin acceso a
internet), así que si football-data.org cambió algún endpoint, puede que
haya que ajustar alguna URL. La documentación oficial está en
https://www.football-data.org/documentation/quickstart
"""
import pandas as pd
import requests
from src.config import FOOTBALL_DATA_API_KEY, FOOTBALL_DATA_BASE_URL, WORLD_CUP_CODE
from src.paths import path as resolve_path

MANUAL_ROUND_PATH = resolve_path("data", "manual_round.json")


def get_manual_round():
    """
    Revisa data/manual_round.json por si el usuario cargó a mano la ronda
    actual (útil cuando la API todavía no actualizó qué partidos quedan,
    como pasa a veces con la Final recién definida). Devuelve
    (round_name, matches) o (None, None) si no hay override cargado.
    """
    import json
    import os

    if not os.path.exists(MANUAL_ROUND_PATH):
        return None, None

    with open(MANUAL_ROUND_PATH, "r") as f:
        data = json.load(f)

    round_name = data.get("round_name")
    matches = data.get("matches", [])

    if not round_name or not matches:
        return None, None

    return round_name, [tuple(m) for m in matches]


def load_historical_data(csv_path: str = None) -> pd.DataFrame:
    """
    Carga el CSV histórico. Espera (al menos) estas columnas:
        date, home_team, away_team, home_score, away_score, tournament

    El dataset recomendado es "International football results from 1872 to
    2026" de Kaggle (Mart Jürisoo / actualizado por la comunidad):
    https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017
    """
    csv_path = csv_path or resolve_path("data", "historical_matches.csv")
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])

    required_cols = {"date", "home_team", "away_team", "home_score", "away_score"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"Al CSV le faltan columnas: {missing}. "
            f"Revisá que el archivo tenga: {required_cols}"
        )

    if "tournament" not in df.columns:
        df["tournament"] = "default"

    return df



# Orden de las rondas eliminatorias tal como las nombra la API. Si en algún
# momento el código de alguna etapa no coincide (no lo pude verificar en
# vivo), revisá la respuesta cruda de la API o la documentación.
KNOCKOUT_STAGE_ORDER = ["QUARTER_FINALS", "SEMI_FINALS", "FINAL"]
THIRD_PLACE_STAGE_CODES = ["THIRD_PLACE", "3RD_PLACE_MATCH", "PLAYOFF_3RD"]


def _fetch_stage_matches(stage: str, status: str = "SCHEDULED") -> list:
    """
    Trae los partidos de una etapa específica (QUARTER_FINALS, SEMI_FINALS,
    FINAL, etc). Devuelve lista de tuplas (local, visitante), descartando
    partidos donde todavía no se conoce alguno de los dos rivales.
    """
    url = f"{FOOTBALL_DATA_BASE_URL}/competitions/{WORLD_CUP_CODE}/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
    params = {"status": status, "stage": stage}

    response = requests.get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    matches = []
    for match in data.get("matches", []):
        home = match["homeTeam"]["name"]
        away = match["awayTeam"]["name"]
        if home is None or away is None:
            continue
        matches.append((home, away))
    return matches


def detect_current_round() -> tuple:
    """
    Recorre las rondas eliminatorias en orden (cuartos -> semis -> final) y
    devuelve la primera que tenga partidos programados con ambos rivales ya
    confirmados. Así el programa se adapta solo a en qué instancia esté el
    torneo el día que lo corras.

    Devuelve (nombre_de_ronda, lista_de_partidos). Si no encuentra ninguna
    ronda pendiente (por ejemplo, si el Mundial ya terminó), devuelve
    (None, []).
    """
    if not FOOTBALL_DATA_API_KEY:
        raise RuntimeError(
            "Falta la API key. Copiá .env.example como .env y completá tu key."
        )

    for stage in KNOCKOUT_STAGE_ORDER:
        matches = _fetch_stage_matches(stage, status="SCHEDULED")
        if matches:
            return stage, matches

    return None, []


def fetch_remaining_world_cup_matches() -> list:
    """
    Mantiene compatibilidad con el resto del código: devuelve solo la lista
    de partidos de la ronda actualmente pendiente (sin el nombre de la ronda).
    """
    _, matches = detect_current_round()
    return matches


def fetch_third_place_match():
    """
    Intenta traer el partido por el tercer puesto. Como no verifiqué en vivo
    cuál código de etapa usa la API para este partido en particular, probamos
    unas variantes conocidas. Si ninguna funciona, devolvemos None y el
    programa sigue sin este partido (no debería frenar el resto).
    """
    if not FOOTBALL_DATA_API_KEY:
        return None

    for stage_code in THIRD_PLACE_STAGE_CODES:
        try:
            matches = _fetch_stage_matches(stage_code, status="SCHEDULED")
            if matches:
                return matches[0]
        except requests.exceptions.HTTPError:
            continue  # ese código de etapa no es válido en esta API, probamos el siguiente

    return None


def fetch_finished_world_cup_matches() -> pd.DataFrame:
    """
    Trae los partidos YA JUGADOS del Mundial 2026 desde la API, útil para
    sumar resultados recientísimos al historial antes de calcular Elo
    (así el modelo no ignora lo que pasó en este mismo torneo).
    """
    if not FOOTBALL_DATA_API_KEY:
        raise RuntimeError(
            "Falta la API key. Copiá .env.example como .env y completá tu key."
        )

    url = f"{FOOTBALL_DATA_BASE_URL}/competitions/{WORLD_CUP_CODE}/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
    params = {"status": "FINISHED"}

    response = requests.get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    rows = []
    for match in data.get("matches", []):
        score = match.get("score", {}).get("fullTime", {})
        if score.get("home") is None:
            continue
        rows.append({
            "date": match["utcDate"][:10],
            "home_team": match["homeTeam"]["name"],
            "away_team": match["awayTeam"]["name"],
            "home_score": score["home"],
            "away_score": score["away"],
            "tournament": "FIFA World Cup",
        })

    return pd.DataFrame(rows)

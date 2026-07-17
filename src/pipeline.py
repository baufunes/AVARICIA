"""
Pipeline central del proyecto: hace TODO el cálculo (datos, Elo, Poisson,
simulación del torneo, córners/tarjetas, gráficos) y devuelve los
resultados en un diccionario.

La idea de tenerlo separado es que tanto main.py (terminal) como gui.py
(ventana Tkinter) llaman a la misma función run_pipeline() y cada uno
decide cómo mostrar el resultado, sin duplicar la lógica.

progress_callback: función opcional que se llama con mensajes de estado
(por ejemplo, para mostrar "Cargando datos..." en la ventana mientras
corre). Si no se pasa nada, simplemente no se emiten esos mensajes.
"""
import pandas as pd
from src.data_fetcher import (
    load_historical_data,
    fetch_finished_world_cup_matches,
    detect_current_round,
    fetch_third_place_match,
    get_manual_round,
)
from src.elo import compute_elo_ratings
from src.poisson_model import compute_team_strengths
from src.bracket_simulator import simulate_tournament
from src.match_simulator import simulate_match
from src.visualize import plot_championship_probabilities, plot_current_round_matchups
from src.stats_predictor import predict_corners_and_cards

FALLBACK_BRACKET = [
    ("France", "Morocco"),
    ("Spain", "Belgium"),
    ("Norway", "England"),
    ("Argentina", "Switzerland"),
]
FALLBACK_ROUND_NAME = "Cuartos de Final"


def _notify(progress_callback, message: str):
    if progress_callback:
        progress_callback(message)


def _build_dataset(progress_callback=None) -> pd.DataFrame:
    _notify(progress_callback, "📂 Cargando historial de partidos...")
    historical = load_historical_data()

    try:
        _notify(progress_callback, "🌐 Sumando partidos ya jugados de este Mundial (API)...")
        wc_matches = fetch_finished_world_cup_matches()
        if not wc_matches.empty:
            wc_matches["date"] = pd.to_datetime(wc_matches["date"])
            historical = pd.concat([historical, wc_matches], ignore_index=True)
            _notify(progress_callback, f"   Sumados {len(wc_matches)} partidos del torneo actual.")
    except Exception as e:
        _notify(progress_callback, f"   ⚠️ No pude traer partidos de la API ({e}). Sigo solo con el histórico.")

    return historical


def _get_current_bracket(progress_callback=None):
    manual_round_name, manual_matches = get_manual_round()
    if manual_round_name:
        _notify(progress_callback, f"📌 Usando ronda cargada a mano: {manual_round_name}")
        return manual_round_name, manual_matches

    try:
        round_name, matches = detect_current_round()
        if matches:
            return round_name, matches
        _notify(progress_callback, "⚠️ La API no devolvió partidos pendientes. Uso el cuadro por defecto.")
    except Exception as e:
        _notify(progress_callback, f"⚠️ No pude detectar la ronda actual vía API ({e}). Uso el cuadro por defecto.")

    return FALLBACK_ROUND_NAME, FALLBACK_BRACKET


def run_pipeline(include_corners_cards: bool = True,
                  n_tournament_sims: int = 10000,
                  progress_callback=None) -> dict:
    """
    Corre todo el pipeline y devuelve un diccionario con:
        round_name, bracket, match_results (uno por cruce, con córners/
        tarjetas si include_corners_cards=True), third_place (o None),
        summary (probabilidades del torneo completo), chart_paths (dict
        con las rutas de los PNG generados).
    """
    matches_df = _build_dataset(progress_callback)

    _notify(progress_callback, "📊 Calculando Elo ratings...")
    elo_ratings = compute_elo_ratings(matches_df)

    _notify(progress_callback, "⚽ Calculando fuerzas de ataque/defensa (Poisson)...")
    strengths, avg_goals = compute_team_strengths(matches_df)

    round_name, bracket = _get_current_bracket(progress_callback)

    _notify(progress_callback, f"🔮 Simulando partidos de {round_name}...")
    match_results = []
    for team_a, team_b in bracket:
        result = simulate_match(team_a, team_b, elo_ratings, strengths, avg_goals)

        if include_corners_cards:
            try:
                extra = predict_corners_and_cards(team_a, team_b)
                result["corners"] = extra["corners"]
                result["cards"] = extra["cards"]
                result["referee"] = extra["referee"]
                result["stats_warnings"] = extra["warnings"]
            except Exception as e:
                result["corners"] = None
                result["cards"] = None
                result["referee"] = None
                result["stats_warnings"] = [f"No pude calcular córners/tarjetas: {e}"]
        else:
            result["corners"] = None
            result["cards"] = None
            result["referee"] = None
            result["stats_warnings"] = []

        match_results.append(result)

    third_place = None
    try:
        tp_teams = fetch_third_place_match()
        if tp_teams:
            team_a, team_b = tp_teams
            third_place = simulate_match(team_a, team_b, elo_ratings, strengths, avg_goals)
    except Exception as e:
        _notify(progress_callback, f"(No pude chequear el partido por el tercer puesto: {e})")

    _notify(progress_callback, f"🎲 Simulando el torneo completo ({n_tournament_sims} corridas)...")
    summary = simulate_tournament(bracket, elo_ratings, strengths, avg_goals, n_sims=n_tournament_sims)

    _notify(progress_callback, "📊 Generando gráficos...")
    chart_paths = {
        "championship": plot_championship_probabilities(summary),
        "current_round": plot_current_round_matchups(match_results, round_name),
    }

    _notify(progress_callback, "✅ Listo.")

    return {
        "round_name": round_name,
        "bracket": bracket,
        "match_results": match_results,
        "third_place": third_place,
        "summary": summary,
        "chart_paths": chart_paths,
    }

"""
Cálculo de Elo rating para selecciones nacionales.

La idea del Elo es simple: cada equipo tiene un puntaje. Antes de cada
partido, calculamos la probabilidad "esperada" de que gane el local según
la diferencia de puntaje. Después del partido, si el resultado real fue
distinto de lo esperado, ajustamos el puntaje de ambos equipos hacia arriba
o hacia abajo.

Un equipo que le gana a un rival mucho más fuerte gana más puntos que si le
gana a uno más débil (porque el resultado era "menos esperado").
"""
from collections import defaultdict
import pandas as pd
from src.config import DEFAULT_ELO, K_FACTOR_BY_TOURNAMENT


def expected_score(rating_a: float, rating_b: float) -> float:
    """
    Probabilidad esperada de que el equipo A le gane al equipo B,
    según la fórmula estándar de Elo.
    """
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def _k_factor(tournament: str) -> int:
    return K_FACTOR_BY_TOURNAMENT.get(tournament, K_FACTOR_BY_TOURNAMENT["default"])


def compute_elo_ratings(matches_df) -> dict:
    """
    Recorre el historial de partidos en orden cronológico y calcula el
    Elo final de cada selección.

    Espera un DataFrame con columnas:
        date, home_team, away_team, home_score, away_score, tournament

    Devuelve un diccionario {equipo: rating_elo}.
    """
    ratings = defaultdict(lambda: DEFAULT_ELO)

    df_sorted = matches_df.copy()
    df_sorted["date"] = pd.to_datetime(df_sorted["date"])
    df_sorted = df_sorted.sort_values("date")

    for _, row in df_sorted.iterrows():
        home, away = row["home_team"], row["away_team"]
        home_goals, away_goals = row["home_score"], row["away_score"]

        rating_home = ratings[home]
        rating_away = ratings[away]

        exp_home = expected_score(rating_home, rating_away)
        exp_away = 1 - exp_home

        if home_goals > away_goals:
            actual_home, actual_away = 1, 0
        elif home_goals < away_goals:
            actual_home, actual_away = 0, 1
        else:
            actual_home, actual_away = 0.5, 0.5

        k = _k_factor(row.get("tournament", "default"))

        # Bonus por goleada: un 4-0 mueve más el rating que un 1-0.
        goal_diff = abs(home_goals - away_goals)
        margin_multiplier = 1 + (goal_diff - 1) * 0.15 if goal_diff > 1 else 1

        ratings[home] = rating_home + k * margin_multiplier * (actual_home - exp_home)
        ratings[away] = rating_away + k * margin_multiplier * (actual_away - exp_away)

    return dict(ratings)


def win_draw_loss_probabilities(rating_a: float, rating_b: float,
                                  draw_weight: float = 0.28) -> tuple:
    """
    A partir de dos ratings de Elo, estima probabilidad de victoria de A,
    empate, y victoria de B.

    El Elo "puro" solo da prob. de victoria/no-victoria (no contempla
    empates), así que restamos una porción fija para el empate y repartimos
    el resto proporcionalmente. draw_weight=0.28 es un valor típico en
    fútbol de selecciones (los empates rondan el 25-30% de los partidos).
    """
    p_a_raw = expected_score(rating_a, rating_b)

    p_draw = draw_weight
    p_a = p_a_raw * (1 - p_draw)
    p_b = (1 - p_a_raw) * (1 - p_draw)

    return p_a, p_draw, p_b

"""
Modelo de Poisson para goles.

Idea: si sabemos cuántos goles convierte y recibe un equipo en promedio,
podemos modelar los goles que va a hacer en un partido puntual como una
variable aleatoria de Poisson.

Usamos una versión simplificada del modelo Dixon-Coles:
    fuerza_ataque(equipo)  = goles_a_favor_promedio(equipo) / goles_promedio_liga
    fuerza_defensa(equipo) = goles_en_contra_promedio(equipo) / goles_promedio_liga

    goles_esperados(local vs visitante) =
        fuerza_ataque(local) * fuerza_defensa(visitante) * goles_promedio_liga * factor_localia
"""
import numpy as np
from scipy.stats import poisson

HOME_ADVANTAGE = 1.15  # jugar de local infla ligeramente los goles esperados


def compute_team_strengths(matches_df) -> dict:
    """
    Calcula fuerza de ataque y defensa de cada equipo a partir del historial.

    Devuelve un dict:
        { equipo: {"attack": float, "defense": float} }
    """
    # Promedio de goles por partido en todo el dataset (referencia general)
    avg_goals = (matches_df["home_score"].mean() + matches_df["away_score"].mean()) / 2

    teams = set(matches_df["home_team"]) | set(matches_df["away_team"])
    strengths = {}

    for team in teams:
        home_games = matches_df[matches_df["home_team"] == team]
        away_games = matches_df[matches_df["away_team"] == team]

        goals_for = home_games["home_score"].sum() + away_games["away_score"].sum()
        goals_against = home_games["away_score"].sum() + away_games["home_score"].sum()
        games_played = len(home_games) + len(away_games)

        if games_played == 0:
            strengths[team] = {"attack": 1.0, "defense": 1.0}
            continue

        avg_scored = goals_for / games_played
        avg_conceded = goals_against / games_played

        strengths[team] = {
            "attack": avg_scored / avg_goals if avg_goals > 0 else 1.0,
            "defense": avg_conceded / avg_goals if avg_goals > 0 else 1.0,
        }

    return strengths, avg_goals


def expected_goals(team_a: str, team_b: str, strengths: dict, avg_goals: float,
                    elo_tilt: float = 0.0) -> tuple:
    """
    Calcula goles esperados para team_a (local) vs team_b (visitante).

    elo_tilt es un ajuste opcional entre -1 y 1 que viene del Elo: si el Elo
    dice que team_a es bastante más fuerte de lo que sugieren sus goles
    históricos (por ejemplo, viene de gran racha reciente), inclinamos un
    poco los goles esperados a su favor, y viceversa.
    """
    s_a = strengths.get(team_a, {"attack": 1.0, "defense": 1.0})
    s_b = strengths.get(team_b, {"attack": 1.0, "defense": 1.0})

    exp_a = s_a["attack"] * s_b["defense"] * avg_goals * HOME_ADVANTAGE
    exp_b = s_b["attack"] * s_a["defense"] * avg_goals

    # Aplicamos el ajuste de Elo (tilt) de forma moderada, no queremos que
    # domine sobre la señal de goles históricos.
    exp_a *= (1 + 0.2 * elo_tilt)
    exp_b *= (1 - 0.2 * elo_tilt)

    return max(exp_a, 0.05), max(exp_b, 0.05)


def simulate_score(exp_goals_a: float, exp_goals_b: float, n_sims: int = 20000) -> np.ndarray:
    """
    Corre n_sims simulaciones de Poisson y devuelve un array de shape
    (n_sims, 2) con los goles simulados de cada equipo.
    """
    goals_a = poisson.rvs(mu=exp_goals_a, size=n_sims)
    goals_b = poisson.rvs(mu=exp_goals_b, size=n_sims)
    return np.column_stack([goals_a, goals_b])

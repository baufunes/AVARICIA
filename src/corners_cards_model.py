"""
Modelos de córners y tarjetas.

CÓRNERS: mismo enfoque que los goles — cada equipo tiene un promedio de
córners a favor/en contra en este Mundial, lo combinamos y simulamos con
Poisson.

TARJETAS: acá el árbitro pesa mucho, así que el número esperado de tarjetas
totales del partido se arma combinando:
  - qué tan "sancionado" es cada equipo en este Mundial (promedio de
    tarjetas recibidas)
  - qué tan tarjetero es el árbitro asignado (promedio de tarjetas que
    reparte por partido, en los partidos de este Mundial que dirigió)

Si no hay datos suficientes de algún equipo o árbitro (por ejemplo, muy
pocos partidos jugados), usamos el promedio general del torneo como
respaldo, para no devolver números sin sentido.
"""
from scipy.stats import poisson
import numpy as np

TOURNAMENT_AVG_CORNERS = 5.0   # córners por equipo por partido, valor típico de referencia
TOURNAMENT_AVG_CARDS = 2.2     # tarjetas amarillas por equipo por partido, valor típico de referencia


def build_team_corner_profile(fixture_stats_list: list, team_name: str) -> dict:
    """
    fixture_stats_list: lista de resultados de fetch_fixture_statistics
    (uno por partido jugado de este equipo).

    Devuelve {"corners_for": prom, "corners_against": prom}.
    """
    corners_for, corners_against = [], []
    for stats in fixture_stats_list:
        for name, values in stats.items():
            if name == team_name:
                corners_for.append(values["corners"])
            else:
                corners_against.append(values["corners"])

    return {
        "corners_for": np.mean(corners_for) if corners_for else TOURNAMENT_AVG_CORNERS,
        "corners_against": np.mean(corners_against) if corners_against else TOURNAMENT_AVG_CORNERS,
    }


def build_team_card_profile(fixture_stats_list: list, team_name: str) -> dict:
    """
    Devuelve el promedio de tarjetas amarillas que recibió el equipo en
    los partidos analizados (las rojas se cuentan aparte por ser mucho
    menos frecuentes y más ruidosas de promediar).
    """
    yellows = []
    for stats in fixture_stats_list:
        for name, values in stats.items():
            if name == team_name:
                yellows.append(values["yellow_cards"])

    return {"cards_for": np.mean(yellows) if yellows else TOURNAMENT_AVG_CARDS}


def build_referee_card_profile(referee_fixture_stats: list) -> dict:
    """
    referee_fixture_stats: lista de resultados de fetch_fixture_statistics
    de los partidos que dirigió este árbitro en el torneo.

    Devuelve el promedio total de tarjetas amarillas que reparte por
    partido (sumando ambos equipos).
    """
    totals = []
    for stats in referee_fixture_stats:
        total = sum(v["yellow_cards"] for v in stats.values())
        totals.append(total)

    avg_total = np.mean(totals) if totals else TOURNAMENT_AVG_CARDS * 2
    return {"avg_cards_per_match": avg_total}


def simulate_corners(team_a_profile: dict, team_b_profile: dict, n_sims: int = 20000) -> dict:
    """
    Simula córners totales de cada equipo en el partido.
    """
    exp_a = (team_a_profile["corners_for"] + team_b_profile["corners_against"]) / 2
    exp_b = (team_b_profile["corners_for"] + team_a_profile["corners_against"]) / 2

    sims_a = poisson.rvs(mu=max(exp_a, 0.5), size=n_sims)
    sims_b = poisson.rvs(mu=max(exp_b, 0.5), size=n_sims)

    return {
        "expected_corners_a": round(exp_a, 1),
        "expected_corners_b": round(exp_b, 1),
        "most_likely_a": int(np.round(np.median(sims_a))),
        "most_likely_b": int(np.round(np.median(sims_b))),
        "prob_over_9_5_total": float((sims_a + sims_b > 9.5).mean()),
    }


def simulate_cards(team_a_card_profile: dict, team_b_card_profile: dict,
                     referee_profile: dict, n_sims: int = 20000) -> dict:
    """
    Simula tarjetas amarillas totales del partido.

    La "tendencia" de los equipos (cuánto suelen recibir) se combina con
    cuánto reparte el árbitro, usando el promedio del torneo como pivote
    para no pisarse: si el árbitro reparte más que el promedio, se
    inclina hacia arriba; si reparte menos, hacia abajo.
    """
    teams_baseline = team_a_card_profile["cards_for"] + team_b_card_profile["cards_for"]
    referee_avg = referee_profile["avg_cards_per_match"]
    referee_factor = referee_avg / (TOURNAMENT_AVG_CARDS * 2)

    expected_total = teams_baseline * referee_factor
    sims_total = poisson.rvs(mu=max(expected_total, 0.5), size=n_sims)

    # Repartimos el total entre los dos equipos proporcionalmente a su
    # propia tendencia (no 50/50), para que el equipo más "sancionado" se
    # lleve la mayor parte de las tarjetas esperadas.
    share_a = team_a_card_profile["cards_for"] / teams_baseline if teams_baseline > 0 else 0.5

    return {
        "expected_total_cards": round(expected_total, 1),
        "expected_cards_a": round(expected_total * share_a, 1),
        "expected_cards_b": round(expected_total * (1 - share_a), 1),
        "most_likely_total": int(np.round(np.median(sims_total))),
        "prob_over_4_5_total": float((sims_total > 4.5).mean()),
        "referee_strictness_vs_avg": round(referee_factor, 2),  # >1 = más tarjetero que el promedio
    }

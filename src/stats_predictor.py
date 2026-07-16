"""
Junta todo lo necesario para predecir córners y tarjetas de UN partido:
  1. Historial de córners/tarjetas de ambos equipos en este Mundial.
  2. Árbitro asignado (si ya está definido) y su historial de tarjetas.
  3. Corre el modelo de simulate_corners / simulate_cards.

Si algo falla (no hay API key, no se identificó el árbitro, error de red),
devuelve lo que se pudo calcular y explica qué faltó, en vez de romper todo
el programa.
"""
from src import api_football
from src.corners_cards_model import (
    build_team_corner_profile,
    build_team_card_profile,
    build_referee_card_profile,
    simulate_corners,
    simulate_cards,
)


def predict_corners_and_cards(team_a: str, team_b: str) -> dict:
    """
    Devuelve un dict con:
        {"corners": {...} | None, "cards": {...} | None,
         "referee": str | None, "warnings": [str, ...]}
    """
    warnings = []
    result = {"corners": None, "cards": None, "referee": None, "warnings": warnings}

    try:
        league_id = api_football.find_world_cup_league_id()
    except Exception as e:
        warnings.append(f"No pude conectar con API-Football: {e}")
        return result

    # --- Perfil de cada equipo, a partir de sus partidos jugados ---
    team_profiles = {}
    for team in (team_a, team_b):
        try:
            fixtures = api_football.fetch_team_world_cup_fixtures(team, league_id)
            stats_list = [api_football.fetch_fixture_statistics(f["fixture_id"]) for f in fixtures]
            team_profiles[team] = {
                "corners": build_team_corner_profile(stats_list, team),
                "cards": build_team_card_profile(stats_list, team),
            }
        except Exception as e:
            warnings.append(f"No pude armar el perfil de {team}: {e}")
            return result

    # --- Córners: no depende del árbitro, ya podemos calcularlo ---
    result["corners"] = simulate_corners(
        team_profiles[team_a]["corners"], team_profiles[team_b]["corners"]
    )

    # --- Árbitro y tarjetas ---
    try:
        referee = api_football.get_manual_referee(team_a, team_b)
        if referee:
            warnings.append(f"Usando árbitro cargado a mano ({referee}), no el de la API.")
        else:
            referee = api_football.find_upcoming_fixture_referee(team_a, team_b, league_id)
        result["referee"] = referee

        if referee:
            referee_stats = api_football.fetch_referee_past_fixtures(referee, league_id)
            referee_profile = build_referee_card_profile(referee_stats)
        else:
            warnings.append("Todavía no está confirmado el árbitro del partido; uso el promedio del torneo.")
            referee_profile = {"avg_cards_per_match": None}
            # Sin árbitro conocido, usamos el promedio general como fallback neutro
            from src.corners_cards_model import TOURNAMENT_AVG_CARDS
            referee_profile["avg_cards_per_match"] = TOURNAMENT_AVG_CARDS * 2

        result["cards"] = simulate_cards(
            team_profiles[team_a]["cards"], team_profiles[team_b]["cards"], referee_profile
        )
    except Exception as e:
        warnings.append(f"No pude calcular la predicción de tarjetas: {e}")

    return result

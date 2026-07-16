"""
Simulador de un partido individual.

Combina las dos señales:
  - Elo: da una "inclinación" (tilt) según qué tan favorito es cada equipo,
    capturando forma reciente y contexto que el promedio de goles histórico
    no ve tan rápido.
  - Poisson: genera el marcador probable partido a partido, miles de veces
    (Monte Carlo), a partir de fuerzas de ataque/defensa.

El resultado es una distribución de probabilidades de victoria/empate/
derrota y de marcadores posibles, no una única predicción "cerrada".
"""
from collections import Counter
from src.elo import expected_score
from src.poisson_model import expected_goals, simulate_score
from src.config import N_SIMULATIONS


def _elo_tilt(rating_a: float, rating_b: float) -> float:
    """
    Convierte la diferencia de Elo en un número entre -1 y 1 que usamos
    para inclinar los goles esperados del modelo de Poisson.
    """
    p = expected_score(rating_a, rating_b)  # 0.5 = parejos
    return (p - 0.5) * 2  # reescala a rango [-1, 1]


def simulate_match(team_a: str, team_b: str, elo_ratings: dict,
                    strengths: dict, avg_goals: float,
                    knockout: bool = True, n_sims: int = N_SIMULATIONS) -> dict:
    """
    Simula un partido entre team_a (local) y team_b (visitante).

    knockout=True significa que, en caso de empate, hay que definir un
    ganador (penales), como corresponde a esta instancia del Mundial.

    Devuelve un diccionario con probabilidades y el marcador más frecuente.
    """
    rating_a = elo_ratings.get(team_a, 1500)
    rating_b = elo_ratings.get(team_b, 1500)
    tilt = _elo_tilt(rating_a, rating_b)

    exp_a, exp_b = expected_goals(team_a, team_b, strengths, avg_goals, elo_tilt=tilt)
    sims = simulate_score(exp_a, exp_b, n_sims=n_sims)

    wins_a = int((sims[:, 0] > sims[:, 1]).sum())
    wins_b = int((sims[:, 0] < sims[:, 1]).sum())
    draws = n_sims - wins_a - wins_b

    scorelines = Counter(map(tuple, sims))
    most_common_score, _ = scorelines.most_common(1)[0]

    result = {
        "team_a": team_a,
        "team_b": team_b,
        "prob_win_a": wins_a / n_sims,
        "prob_draw": draws / n_sims,
        "prob_win_b": wins_b / n_sims,
        "expected_goals_a": round(exp_a, 2),
        "expected_goals_b": round(exp_b, 2),
        "most_likely_score": f"{most_common_score[0]}-{most_common_score[1]}",
    }

    if knockout:
        # En eliminación directa, si hay empate, lo resolvemos con la
        # probabilidad pre-partido (proxy simple de "quién define mejor
        # los penales" sería más data que no tenemos; usamos la prob. base
        # como estimador razonable de quién avanza en caso de igualdad).
        base_prob_a = wins_a + draws * (wins_a / (wins_a + wins_b)) if (wins_a + wins_b) > 0 else wins_a + draws / 2
        result["prob_advance_a"] = base_prob_a / n_sims
        result["prob_advance_b"] = 1 - result["prob_advance_a"]

    return result

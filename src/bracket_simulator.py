"""
Simula el cuadro eliminatorio completo del Mundial (desde donde esté el
torneo: cuartos, semis, final) miles de veces, y agrega estadísticas de
cuántas veces llega cada equipo a cada instancia y cuántas veces sale campeón.
"""
import random
import math
from collections import defaultdict
from src.match_simulator import simulate_match
from src.config import N_SIMULATIONS


def _stage_labels(n_initial_matches: int) -> list:
    """
    Calcula dinámicamente los nombres de las etapas que se van alcanzando,
    según cuántos partidos tenga la ronda inicial del bracket.

    Por ejemplo, si arrancamos con 4 partidos (cuartos, 8 equipos):
        ["Semifinal", "Final", "Campeón"]
    Si arrancamos con 2 partidos (semis, 4 equipos):
        ["Final", "Campeón"]
    Si arrancamos con 1 partido (la final misma):
        ["Campeón"]
    """
    names_by_size = {8: "Cuartos de Final", 4: "Semifinal", 2: "Final", 1: "Campeón"}
    labels = []
    teams = n_initial_matches * 2
    while teams > 1:
        teams //= 2
        labels.append(names_by_size.get(teams, f"Ronda de {teams}"))
    return labels


def _played_round_labels(n_initial_matches: int) -> list:
    """
    Nombres de las rondas que se van JUGANDO (a diferencia de _stage_labels,
    que da la etapa que se ALCANZA al ganar). Por ejemplo, con un bracket de
    4 partidos: ["Cuartos de Final", "Semifinal", "Final"].
    """
    names_by_size = {8: "Cuartos de Final", 4: "Semifinal", 2: "Final"}
    labels = []
    teams = n_initial_matches * 2
    while teams > 1:
        labels.append(names_by_size.get(teams, f"Ronda de {teams}"))
        teams //= 2
    return labels


def simulate_bracket_once(bracket: list, elo_ratings: dict, strengths: dict,
                            avg_goals: float) -> dict:
    """
    bracket: lista de partidos de la ronda actual, cada uno una tupla
             (equipo_local, equipo_visitante).

    Devuelve el recorrido de esa única simulación: qué equipo avanzó en
    cada cruce, ronda por ronda, hasta el campeón.
    """
    round_results = []
    current_round = bracket
    round_names = _played_round_labels(len(bracket))
    round_idx = 0

    while len(current_round) >= 1:
        winners = []
        round_name = round_names[round_idx] if round_idx < len(round_names) else f"Ronda {round_idx+1}"

        for team_a, team_b in current_round:
            match = simulate_match(team_a, team_b, elo_ratings, strengths,
                                     avg_goals, knockout=True, n_sims=1)
            # Para una corrida individual usamos la probabilidad de avance
            # como una moneda cargada (bernoulli), no la simulación de 1
            # partido de Poisson puro (que sería muy ruidosa).
            prob_a = match["prob_advance_a"]
            winner = team_a if random.random() < prob_a else team_b
            winners.append(winner)

        round_results.append({"round": round_name, "matchups": current_round, "winners": winners})

        if len(winners) == 1:
            break

        current_round = [(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)]
        round_idx += 1

    champion = round_results[-1]["winners"][0]
    return {"rounds": round_results, "champion": champion}


def simulate_tournament(bracket: list, elo_ratings: dict, strengths: dict,
                          avg_goals: float, n_sims: int = 10000) -> dict:
    """
    Corre la simulación del torneo n_sims veces y agrega resultados:
    cuántas veces cada equipo fue campeón, llegó a la final, a semis, etc.

    Nota: acá usamos probabilidades pre-calculadas por cruce (más rápido
    que recalcular Poisson en cada una de las n_sims corridas), así que
    primero resolvemos las probabilidades de avance de la ronda actual una
    sola vez, y las vamos reutilizando partido a partido según quién
    efectivamente llegue a cada cruce.
    """
    stage_reach_counts = defaultdict(lambda: defaultdict(int))  # {equipo: {ronda: veces}}
    champion_counts = defaultdict(int)

    # Cacheamos probabilidades de partidos ya vistos para no recalcular
    # Poisson de más (mismos dos equipos = mismo resultado esperado).
    match_cache = {}

    def get_match(team_a, team_b):
        key = tuple(sorted([team_a, team_b]))
        if key not in match_cache:
            match_cache[key] = simulate_match(team_a, team_b, elo_ratings,
                                                strengths, avg_goals,
                                                knockout=True, n_sims=2000)
        m = match_cache[key]
        # Si el orden real es distinto al orden cacheado, invertimos las probs.
        if m["team_a"] == team_a:
            return m["prob_advance_a"]
        return m["prob_advance_b"]

    # El ganador de cada ronda AVANZA a la siguiente etapa (no "alcanza" la
    # ronda que acaba de jugar), así que mapeamos ronda jugada -> etapa alcanzada.
    next_stage_names = _stage_labels(len(bracket))

    for _ in range(n_sims):
        current_round = bracket
        round_idx = 0

        while True:
            winners = []
            stage_reached = next_stage_names[round_idx] if round_idx < len(next_stage_names) else f"Ronda {round_idx+2}"

            for team_a, team_b in current_round:
                prob_a = get_match(team_a, team_b)
                winner = team_a if random.random() < prob_a else team_b
                winners.append(winner)
                if stage_reached != "Campeón":  # el título ya se cuenta aparte
                    stage_reach_counts[winner][stage_reached] += 1

            if len(winners) == 1:
                champion_counts[winners[0]] += 1
                break

            current_round = [(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)]
            round_idx += 1

    summary = {
        team: {
            "prob_champion": champion_counts.get(team, 0) / n_sims,
            **{
                f"prob_reach_{stage.lower().replace(' ', '_')}": count / n_sims
                for stage, count in stages.items()
            },
        }
        for team, stages in stage_reach_counts.items()
    }

    return summary

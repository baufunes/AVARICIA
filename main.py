"""
Punto de entrada por terminal.

Corré esto con:  python main.py

Toda la lógica de cálculo vive en src/pipeline.py (así la comparte con
gui.py, la ventana de escritorio). Este archivo solo se encarga de imprimir
los resultados de forma legible.
"""
from src.pipeline import run_pipeline


def print_match_result(team_a: str, team_b: str, result: dict):
    print(f"\n{team_a} vs {team_b}")
    print(f"  Marcador más probable: {result['most_likely_score']}")
    print(f"  Gana {team_a}: {result['prob_win_a']:.1%}  |  "
          f"Empate: {result['prob_draw']:.1%}  |  "
          f"Gana {team_b}: {result['prob_win_b']:.1%}")
    if "prob_advance_a" in result:
        print(f"  Avanza {team_a}: {result['prob_advance_a']:.1%}  |  "
              f"Avanza {team_b}: {result['prob_advance_b']:.1%}")

    if result.get("corners"):
        c = result["corners"]
        print(f"  Córners esperados: {team_a} {c['expected_corners_a']} - "
              f"{c['expected_corners_b']} {team_b}")
    if result.get("cards"):
        cd = result["cards"]
        ref_note = f" (árbitro: {result['referee']})" if result.get("referee") else " (árbitro aún no confirmado)"
        print(f"  Tarjetas amarillas esperadas: {cd['expected_total_cards']} en total"
              f" ({cd['expected_cards_a']} - {cd['expected_cards_b']}){ref_note}")
    for w in result.get("stats_warnings", []):
        print(f"  ⚠️  {w}")


def main():
    data = run_pipeline(progress_callback=print)

    print("\n" + "=" * 60)
    print(f"PROBABILIDADES POR CRUCE — {data['round_name'].upper()}")
    print("=" * 60)
    for (team_a, team_b), result in zip(data["bracket"], data["match_results"]):
        print_match_result(team_a, team_b, result)

    if data["third_place"]:
        tp = data["third_place"]
        print("\n" + "=" * 60)
        print("PARTIDO POR EL TERCER PUESTO")
        print("=" * 60)
        print_match_result(tp["team_a"], tp["team_b"], tp)

    print("\n" + "=" * 60)
    print("SIMULACIÓN DEL CAMINO AL TÍTULO")
    print("=" * 60)
    ranked = sorted(data["summary"].items(), key=lambda x: x[1]["prob_champion"], reverse=True)
    print(f"\n{'Equipo':<15} {'% Campeón':<12} {'% Llega a Final':<16} {'% Llega a Semi':<14}")
    for team, stats in ranked:
        print(f"{team:<15} "
              f"{stats.get('prob_champion', 0):<12.1%} "
              f"{stats.get('prob_reach_final', 0):<16.1%} "
              f"{stats.get('prob_reach_semifinal', 0):<14.1%}")

    print(f"\nGráficos guardados en: {list(data['chart_paths'].values())}")


if __name__ == "__main__":
    main()

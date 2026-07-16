"""
Gráficos con matplotlib. Se guardan como archivos PNG en la carpeta
outputs/ (se crea sola si no existe).
"""
import os
import matplotlib
matplotlib.use("Agg")  # no necesita entorno gráfico para generar el PNG
import matplotlib.pyplot as plt
from src.paths import path as resolve_path

TEAM_COLOR = "#2E86AB"
OPPONENT_COLOR = "#A23B72"


def plot_championship_probabilities(summary: dict, save_path: str = None) -> str:
    """
    Gráfico de barras horizontales con la probabilidad de cada selección
    de salir campeona, de mayor a menor.
    """
    save_path = save_path or resolve_path("outputs", "probabilidades_campeon.png")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    ranked = sorted(summary.items(), key=lambda x: x[1]["prob_champion"], reverse=True)
    names = [team for team, _ in ranked]
    probs = [stats["prob_champion"] * 100 for _, stats in ranked]

    fig, ax = plt.subplots(figsize=(8, max(3, 0.5 * len(names))))
    bars = ax.barh(names, probs, color=TEAM_COLOR)
    ax.invert_yaxis()  # el más probable arriba
    ax.set_xlabel("Probabilidad de ser campeón (%)")
    ax.set_title("Probabilidad de salir campeón — Mundial 2026")
    ax.set_xlim(0, max(probs) * 1.2 if probs else 100)

    for bar, prob in zip(bars, probs):
        ax.text(bar.get_width() + max(probs) * 0.01, bar.get_y() + bar.get_height() / 2,
                 f"{prob:.1f}%", va="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"📊 Gráfico guardado en: {save_path}")
    return save_path


def plot_current_round_matchups(match_results: list, round_name: str,
                                  save_path: str = None) -> str:
    """
    Un mini-gráfico de barras por cada cruce de la ronda actual, mostrando
    la probabilidad de avanzar de cada equipo.

    match_results: lista de dicts devueltos por simulate_match (uno por cruce).
    """
    save_path = save_path or resolve_path("outputs", "cuadro_ronda_actual.png")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    n = len(match_results)
    fig, axes = plt.subplots(n, 1, figsize=(6, 2.2 * n))
    if n == 1:
        axes = [axes]

    for ax, match in zip(axes, match_results):
        team_a, team_b = match["team_a"], match["team_b"]
        prob_a = match.get("prob_advance_a", match["prob_win_a"]) * 100
        prob_b = match.get("prob_advance_b", match["prob_win_b"]) * 100

        ax.barh([team_b, team_a], [prob_b, prob_a], color=[OPPONENT_COLOR, TEAM_COLOR])
        ax.set_xlim(0, 100)
        ax.set_title(f"{team_a}  vs  {team_b}   (marcador probable: {match['most_likely_score']})",
                     fontsize=10, loc="left")
        for i, prob in enumerate([prob_b, prob_a]):
            ax.text(prob + 1, i, f"{prob:.0f}%", va="center", fontsize=9)

    fig.suptitle(f"Probabilidad de avanzar — {round_name}", fontsize=13)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"📊 Gráfico guardado en: {save_path}")
    return save_path

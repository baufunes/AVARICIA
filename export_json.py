"""
Corre todo el pipeline de predicción y guarda el resultado en
docs/data/predictions.json — ese archivo es lo que lee la página web
(docs/index.html + script.js).

Lo corre automáticamente GitHub Actions cada tantas horas, pero también lo
podés correr vos a mano en cualquier momento:

    python export_json.py
"""
import json
import os
from datetime import datetime, timezone
import numpy as np
from src.pipeline import run_pipeline

OUTPUT_PATH = "docs/data/predictions.json"


def _json_default(obj):
    """
    numpy usa sus propios tipos de número (np.float64, np.int64) que el
    módulo json de Python no sabe convertir solo. Esta función le explica
    cómo pasarlos a float/int normales.
    """
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    raise TypeError(f"No sé serializar el tipo {type(obj)}")


def _serialize_match(team_a: str, team_b: str, result: dict) -> dict:
    return {
        "team_a": team_a,
        "team_b": team_b,
        "most_likely_score": result.get("most_likely_score"),
        "prob_win_a": result.get("prob_win_a"),
        "prob_draw": result.get("prob_draw"),
        "prob_win_b": result.get("prob_win_b"),
        "prob_advance_a": result.get("prob_advance_a"),
        "prob_advance_b": result.get("prob_advance_b"),
        "corners": result.get("corners"),
        "cards": result.get("cards"),
        "referee": result.get("referee"),
        "warnings": result.get("stats_warnings", []),
    }


def main():
    data = run_pipeline(progress_callback=print)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "round_name": data["round_name"],
        "matches": [
            _serialize_match(team_a, team_b, result)
            for (team_a, team_b), result in zip(data["bracket"], data["match_results"])
        ],
        "third_place": None,
        "champions": [
            {"team": team, **stats}
            for team, stats in sorted(
                data["summary"].items(), key=lambda x: x[1]["prob_champion"], reverse=True
            )
        ],
    }

    if data["third_place"]:
        tp = data["third_place"]
        output["third_place"] = _serialize_match(tp["team_a"], tp["team_b"], tp)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=_json_default)

    print(f"✅ Guardado en {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

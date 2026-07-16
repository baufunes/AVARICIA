// ============================================================
// script.js — arma toda la página a partir de data/predictions.json
//
// La idea general (si estás aprendiendo JS, este es el resumen):
//   1. Pedimos el archivo JSON con fetch() (es una promesa: el código
//      sigue corriendo mientras se descarga, y "then" se ejecuta cuando
//      ya está listo).
//   2. Una vez que tenemos los datos, generamos el HTML de cada sección
//      armando strings con template literals (los `texto ${variable}`).
//   3. Insertamos ese HTML en la página con .innerHTML.
// ============================================================

const DATA_URL = "data/predictions.json";

async function init() {
  try {
    const response = await fetch(DATA_URL);
    if (!response.ok) {
      throw new Error(`No pude cargar el JSON (status ${response.status})`);
    }
    const data = await response.json();
    render(data);
  } catch (error) {
    showError(error);
  }
}

function render(data) {
  document.getElementById("subtitle").textContent =
    `Ronda actual: ${data.round_name}`;
  document.getElementById("last-updated").textContent =
    formatDate(data.generated_at);

  const app = document.getElementById("app");
  app.innerHTML = ""; // limpiamos el "Cargando..."

  app.appendChild(buildSection(`Cuartos de Final`, buildMatchesHTML(data.matches)));

  if (data.third_place) {
    app.appendChild(
      buildSection("Partido por el Tercer Puesto", buildMatchesHTML([data.third_place]))
    );
  }

  app.appendChild(buildSection("Probabilidad de salir campeón", buildChampionsHTML(data.champions)));
}

// --- Helpers para armar cada sección ---

function buildSection(title, innerHTML) {
  const section = document.createElement("section");
  section.innerHTML = `<h2 class="section-title">${title}</h2>${innerHTML}`;
  return section;
}

function buildMatchesHTML(matches) {
  return matches.map(buildMatchCardHTML).join("");
}

function buildMatchCardHTML(match) {
  const probA = match.prob_win_a * 100;
  const probDraw = match.prob_draw * 100;
  const probB = match.prob_win_b * 100;

  // Los detalles extra (córners, tarjetas, árbitro) son opcionales: puede
  // que la API todavía no los tenga disponibles para este partido.
  const details = [];
  if (match.corners) {
    details.push(
      `<div>🚩 <strong>Córners esperados:</strong> ${match.team_a} ${match.corners.expected_corners_a} - ${match.corners.expected_corners_b} ${match.team_b}</div>`
    );
  }
  if (match.cards) {
    const ref = match.referee ? `árbitro: ${match.referee}` : "árbitro sin confirmar";
    details.push(
      `<div>🟨 <strong>Tarjetas esperadas:</strong> ${match.cards.expected_total_cards} en total (${ref})</div>`
    );
  }
  if (match.prob_advance_a !== null && match.prob_advance_a !== undefined) {
    details.push(
      `<div>➡️ <strong>Avanza:</strong> ${match.team_a} ${(match.prob_advance_a * 100).toFixed(0)}% / ${match.team_b} ${(match.prob_advance_b * 100).toFixed(0)}%</div>`
    );
  }

  const warnings = (match.warnings || [])
    .map((w) => `<div class="match-warning">⚠️ ${w}</div>`)
    .join("");

  return `
    <div class="match-card">
      <div class="match-teams">
        <h3>${match.team_a} vs ${match.team_b}</h3>
        <span class="match-score">Marcador probable: ${match.most_likely_score}</span>
      </div>

      <div class="prob-bar">
        ${buildProbSegment(match.team_a, probA, "team-a")}
        ${buildProbSegment("Empate", probDraw, "draw")}
        ${buildProbSegment(match.team_b, probB, "team-b")}
      </div>

      <div class="match-details">
        ${details.join("")}
      </div>
      ${warnings}
    </div>
  `;
}

function buildProbSegment(label, percent, cssClass) {
  // Si el segmento es muy angosto, no le ponemos texto adentro (no entra
  // legible), pero igual queda representado el ancho proporcional.
  const text = percent >= 12 ? `${label} ${percent.toFixed(0)}%` : "";
  return `<div class="prob-segment ${cssClass}" style="width:${percent}%">${text}</div>`;
}

function buildChampionsHTML(champions) {
  return `
    <div class="champions-list">
      ${champions
        .map((c) => {
          const percent = (c.prob_champion * 100).toFixed(1);
          return `
            <div class="champion-row">
              <span class="champion-name">${c.team}</span>
              <div class="champion-bar-track">
                <div class="champion-bar-fill" style="width:${percent}%"></div>
              </div>
              <span class="champion-percent">${percent}%</span>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function formatDate(isoString) {
  if (!isoString) return "-";
  const date = new Date(isoString);
  return date.toLocaleString("es-AR", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function showError(error) {
  console.error(error);
  document.getElementById("app").innerHTML = `
    <p style="color:#f0c808">
      ⚠️ No pude cargar las predicciones. Puede que el archivo
      data/predictions.json todavía no se haya generado (o falló la última
      actualización automática). Detalle técnico: ${error.message}
    </p>
  `;
}

// Arrancamos apenas carga la página
init();

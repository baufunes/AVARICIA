# Simulador / Predictor del Mundial 2026 — versión web

Simula los partidos que quedan del Mundial 2026 combinando:
- **Elo rating**: fuerza relativa de cada selección, actualizada partido a partido.
- **Poisson**: distribución de goles esperados según fuerza de ataque/defensa.
- **Córners y tarjetas**: usando el historial de cada equipo y del árbitro asignado, en este mismo Mundial.

Corre miles de simulaciones Monte Carlo por partido y por torneo para dar
probabilidades (no una única predicción "cerrada").

**Cómo funciona la versión web:** un robot de GitHub (GitHub Actions) corre
el motor de Python cada 6 horas automáticamente, guarda el resultado en un
archivo JSON, y una página HTML/CSS/JS lo lee y lo muestra. No hay ningún
servidor que mantener prendido — es una página estática, gratis, que
funciona en cualquier sistema operativo con solo entrar a una URL (arregla
de raíz el problema de que tu compañero no podía abrir el `.app` de Mac).

## Estructura del proyecto

```
worldcup_predictor/
├── export_json.py            ← Genera docs/data/predictions.json
├── main.py                   ← (opcional) correr por terminal, igual que antes
├── requirements.txt
├── .env.example               ← Copiar a .env con tus API keys (uso LOCAL)
├── .github/workflows/
│   └── update_predictions.yml  ← El robot que actualiza la web solo
├── data/
│   ├── historical_matches.csv    ← Vos lo bajás de Kaggle (ver paso 3)
│   ├── manual_referees.json      ← Cargar árbitros a mano
│   └── api_football_cache.json   ← Se crea sola (caché de requests)
├── docs/                       ← ESTO es la página web (GitHub Pages la sirve desde acá)
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   └── data/predictions.json     ← Se genera y actualiza solo
└── src/
    ├── config.py, paths.py, elo.py, poisson_model.py, match_simulator.py,
    ├── bracket_simulator.py, data_fetcher.py, api_football.py,
    ├── corners_cards_model.py, stats_predictor.py, visualize.py, pipeline.py
```

## Paso 1 — Preparar todo localmente (como ya veníamos haciendo)

```bash
cd worldcup_predictor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Completá `.env` con tus dos API keys (football-data.org y API-Football),
como en los pasos anteriores. Esto es para poder probar en tu máquina
antes de subir nada — en la nube, las keys se configuran distinto (ver Paso 5).

## Paso 2 — Conseguir el histórico de Kaggle

Bajá `results.csv` de
[este dataset de Kaggle](https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017),
renombralo a `historical_matches.csv` y ponelo en `data/`.

⚠️ Antes de hacer público el repo (paso 4), revisá la licencia del dataset
en la página de Kaggle — la mayoría de estos datasets permiten
redistribución, pero conviene confirmarlo antes de subirlo.

## Paso 3 — Probar que todo funcione localmente

```bash
python export_json.py
```

Esto debería crear `docs/data/predictions.json`. Para ver la página como
la va a ver cualquiera en internet, corré un servidor local:

```bash
cd docs
python3 -m http.server 8000
```

Y abrí `http://localhost:8000` en el navegador. Si ves las tarjetas de
partidos con las probabilidades, vas bien encaminado.

## Paso 4 — Crear el repositorio en GitHub

1. Andá a [github.com/new](https://github.com/new) y creá un repo nuevo
   (por ejemplo `worldcup-predictor`). Dejalo **público** (necesario para
   GitHub Pages gratis, salvo que tengas GitHub Pro).
2. **No** marques "Add a README" ni ".gitignore" — ya los tenemos.

En tu terminal, parado en la carpeta `worldcup_predictor`:

```bash
git init
git add .
git commit -m "Primera versión del simulador"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/worldcup-predictor.git
git push -u origin main
```

Qué hace cada línea:
- `git init` — convierte esta carpeta en un repositorio de git (una sola vez).
- `git add .` — marca todos los archivos para el próximo commit.
- `git commit -m "..."` — guarda una "foto" de todo con un mensaje descriptivo.
- `git branch -M main` — nombra la rama principal "main" (estándar actual).
- `git remote add origin ...` — conecta tu carpeta local con el repo de GitHub (reemplazá la URL por la tuya, GitHub te la muestra al crear el repo).
- `git push -u origin main` — sube todo a GitHub por primera vez.

De ahí en adelante, cada vez que quieras subir cambios nuevos, alcanza con:
```bash
git add .
git commit -m "Descripción del cambio"
git push
```

## Paso 5 — Cargar tus API keys como Secrets de GitHub

Tus keys **nunca** van directo al código (por eso `.env` está en
`.gitignore` y no se sube). En su lugar:

1. En tu repo de GitHub, andá a **Settings > Secrets and variables > Actions**.
2. Click en **New repository secret**.
3. Creá dos secrets:
   - Nombre: `FOOTBALL_DATA_API_KEY` — Valor: tu key de football-data.org
   - Nombre: `API_FOOTBALL_KEY` — Valor: tu key de API-Football

El robot de GitHub Actions los va a usar automáticamente (mirá el
`env:` dentro de `.github/workflows/update_predictions.yml`).

## Paso 6 — Activar GitHub Pages

1. En tu repo, andá a **Settings > Pages**.
2. En "Source", elegí **Deploy from a branch**.
3. Rama: **main**, carpeta: **/docs**. Guardá.
4. GitHub te va a dar una URL tipo `https://tu-usuario.github.io/worldcup-predictor/`
   (puede tardar 1-2 minutos en activarse la primera vez).

## Paso 7 — Probar que el robot funcione

No hace falta esperar 6 horas para la primera prueba:

1. Andá a la pestaña **Actions** de tu repo.
2. Click en **Actualizar predicciones** (a la izquierda).
3. Click en **Run workflow** (botón a la derecha) > **Run workflow**.
4. Esperá un minuto y refrescá — debería aparecer con un tilde verde ✅.
5. Entrá a tu URL de GitHub Pages y confirmá que se vean las predicciones.

Si el tilde sale rojo ❌, hacé click en la corrida fallida para ver el
log — casi siempre es un Secret mal escrito o el CSV histórico faltante.

## Compartir el link con tu compañero

Una vez que todo esto ande, el link de GitHub Pages (`https://tu-usuario.github.io/worldcup-predictor/`)
es todo lo que necesita tu compañero — nada de instalar Python, nada de
Mac vs Windows, solo abrir el link en cualquier navegador.

## Cargar un árbitro a mano (cuando la API todavía no lo tiene)

Editá `data/manual_referees.json` (en tu máquina), y hacé `git add`, `git
commit`, `git push` para que se refleje en la web:

```json
{
  "Argentina|Switzerland": "João Pinheiro"
}
```

## Notas honestas sobre las limitaciones

- No pude probar ninguno de los dos endpoints de API en vivo desde mi
  entorno de trabajo (sin acceso a internet), ni tampoco pude probar el
  workflow de GitHub Actions corriendo de verdad (no tengo una cuenta de
  GitHub desde acá). Validé toda la lógica de Python y la sintaxis del
  YAML, pero si algo falla en la corrida real, pasame el log del Actions
  tal cual y lo ajustamos.
- El código de etapa exacto para "tercer puesto" en football-data.org no
  lo pude confirmar en vivo — el programa prueba variantes conocidas.
- **Córners y tarjetas usan solo datos de este Mundial 2026**, no toda la
  carrera del equipo/árbitro, para no gastar de más el límite gratuito de
  API-Football (100 requests/día).
- El cron job corre en horario UTC, no en horario de Argentina — `0 */6 * * *`
  corre a las 00:00, 06:00, 12:00 y 18:00 UTC (21:00, 03:00, 09:00 y 15:00
  en Argentina, aproximadamente, dependiendo del horario de verano).
- Con el plan gratuito de GitHub, un repo público tiene minutos de Actions
  ilimitados para este tipo de uso — no debería haber costo.

## Próximos pasos posibles

- Reemplazar las barras de probabilidad hechas a mano por gráficos con
  Chart.js (interactivos, con tooltips).
- Guardar un historial de predicciones pasadas para comparar cómo
  cambiaron con el tiempo.
- Agregar un modo oscuro/claro con un botón (ya está todo en variables CSS,
  sería cuestión de armar el toggle).
- Extender a otros deportes o campeonatos.

Cualquier paso de estos, decime y lo armamos juntos.

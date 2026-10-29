# WindSight

WindSight is a React and FastAPI dashboard for comparing UK wind generation forecasts with Elexon wind generation outturn. The default view is January 1–31, 2026. It selects the forecast available before a documented day-ahead cutoff and reports the matched coverage alongside accuracy metrics.

## Data and method

WindSight uses the public, keyless [Elexon Insights API](https://developer.data.elexon.co.uk/):

- [`FUELHH/stream`](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) supplies half-hourly average generation in MW by fuel type. The backend requests `fuelType=WIND`.
- [`WINDFOR/stream`](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) supplies forecast `generation` in MW with `startTime` and `publishTime`. Elexon's [wind generation notes](https://bmrs.elexon.co.uk/wind-generation) describe this series as hourly and explain its forecast horizon and publication updates.

The backend queries actuals by settlement date and forecasts by publication time. For each half-hour actual period, it uses the latest forecast published at or before **12:00 UTC on the previous day**. This is the assignment's documented day-ahead cutoff assumption; it is not presented as an official market purchasing deadline. WINDFOR is hourly, so an hourly forecast is held constant for its two half-hour FUELHH periods. The UI and coverage metrics make this resolution difference visible.

Timestamps are interpreted in UTC. The backend does not shift missing periods or fill absent observations. It filters malformed rows, reports duplicate and missing observations, and computes error metrics only from matched forecast/actual periods. Error is forecast minus actual, so a positive bias means overforecasting.

- **MAE:** mean absolute error in MW.
- **RMSE:** square root of mean squared error in MW.
- **Bias:** mean signed error in MW.
- **MAPE:** mean absolute percentage error for matched periods with non-zero actuals; it is null when no valid denominator exists.
- **Coverage:** matched half-hour periods divided by the 48-per-day half-hour periods in the selected date range.

### January 2026 validation

The live backend completed the full January query on October 29, 2026: 1,488 filtered FUELHH wind records and 19,053 WINDFOR records in the needed publication window produced 1,488 matched half-hour periods (100% coverage). That run returned MAE 2,020.6 MW, RMSE 2,481.4 MW, bias +1,806.2 MW, and MAPE 19.7%. The unfiltered January FUELHH stream was also checked and returned 29,760 rows across fuel types. The response fields inspected were `fuelType`, `startTime`, `settlementDate`, `settlementPeriod`, `publishTime`, and `generation`. These are recorded validation results; no observed values or metrics are hard-coded in the app.

The repository does not bundle a static copy of the January data. At runtime the API must be reachable from the backend host; otherwise the dashboard returns a clear unavailable-data state. Successful responses are cached under `backend/.cache` for repeat requests.

Elexon describes the data as applying to wind farms visible to NESO with operational metering. It should not be read as a complete measure of all embedded or unmetered wind generation. See the [Elexon data licence and API terms](https://developer.data.elexon.co.uk/) before redistributing raw records.

## Run locally

Python 3.12+ and Node.js 22+ are recommended.

1. From the repository root, copy `.env.example` to `.env`. No Elexon API key is required.
2. In PowerShell, install and start the backend:

   ```powershell
   cd backend
   py -m venv .venv-local
   .\.venv-local\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. In a second terminal, install and start the frontend:

   ```powershell
   cd frontend
   npm ci
   npm run dev -- --host 0.0.0.0 --port 5173
   ```

4. Open <http://localhost:5173>. The backend health check is <http://localhost:8000/api/health>.

The root `.env` supports `ELEXON_BASE_URL`, `CORS_ORIGINS`, the default date range, and `FORECAST_CUTOFF_UTC_HOUR`. The frontend defaults to `http://localhost:8000`; set `VITE_API_BASE_URL` in the frontend build environment when the API is hosted elsewhere.

Use a fresh `.venv-local` if an existing `.venv` reports that its Python executable is missing. The existing environment in this workspace points to an unavailable Python 3.12 installation.

## Docker Compose

From the repository root:

```powershell
docker compose up --build
```

The frontend is served at <http://localhost:5173> and the API at <http://localhost:8000>. Docker Desktop must be running.

## Verification

Run the backend tests and production frontend build:

```powershell
cd backend
python -m pytest -q
cd ..\frontend
npm run build
```

The tests mock Elexon responses and do not require network access.

## API

- `GET /api/health`
- `GET /api/metadata`
- `GET /api/dashboard?start_date=2026-01-01&end_date=2026-01-31`
- `GET /api/accuracy?start_date=2026-01-01&end_date=2026-01-31`
- `GET /api/errors?start_date=2026-01-01&end_date=2026-01-31&limit=10`
- `GET /api/forecast-history?start_date=2026-01-01&end_date=2026-01-31&target_time=2026-01-15T12:00:00Z`

## Deployment and submission

### Live deployment

- **Frontend:** https://wind-sight-pi.vercel.app/
- **Backend API:** https://windsight-zvxb.onrender.com
- **Health check:** https://windsight-zvxb.onrender.com/api/health
- **GitHub repository:** https://github.com/AVI21090/xqv731

The frontend is deployed on Vercel and the FastAPI backend is deployed on Render.

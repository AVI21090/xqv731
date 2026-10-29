# WindSight demo script

Total time: 10 minutes maximum, split into two sections of up to five minutes each. Use January 1–31, 2026 for the walkthrough. Confirm the backend can reach Elexon before recording; if it cannot, explain the unavailable state and do not present empty values as measured results.

## Part 1 — Customer walkthrough (5 minutes)

- **0:00–0:45:** Describe the day-ahead procurement question: how close was the forecast available before buying to the eventual wind outturn?
- **0:45–1:30:** Set January 2026 and point out the Elexon source, retrieval time, and selected date range.
- **1:30–2:30:** Read the forecast-versus-actual chart. Explain that the forecast is hourly and displayed across its two half-hour actual periods.
- **2:30–3:30:** Explain matched periods, coverage, MAE, RMSE, bias, and MAPE. Positive bias means forecast generation exceeded actual generation.
- **3:30–4:30:** Show the largest errors and the publication history for the selected target period. Explain the prior-day 12:00 UTC eligibility cutoff.
- **4:30–5:00:** State the limitations: the cutoff is an assignment assumption; Elexon wind data covers farms visible to NESO with operational metering; missing source rows are left unmatched.

## Part 2 — Technical walkthrough (5 minutes)

- **0:00–0:45:** Show the React/Vite frontend and FastAPI backend and the dashboard, accuracy, errors, and forecast-history endpoints.
- **0:45–1:45:** Show the public Elexon FUELHH and WINDFOR stream endpoints. Point out the actual fuel filter and the forecast publication and delivery timestamps. No API key is required.
- **1:45–2:45:** Walk through UTC timestamp handling, the previous-day 12:00 UTC cutoff, hourly forecast alignment to half-hour actuals, and missing-period handling.
- **2:45–3:40:** Show the metric code and deterministic mocked tests, including cutoff, zero-actual, and missing-record cases.
- **3:40–4:20:** Show Docker Compose and the health check. Mention that the local compose run requires Docker Desktop.
- **4:20–5:00:** Close with deployment status. The public service URLs, unlisted recording, and assignment form must be completed by the submitter using their accounts.

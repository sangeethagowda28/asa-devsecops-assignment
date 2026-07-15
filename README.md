# VulnTracker

VulnTracker is a two-service system for managing vulnerability scan results:

- **`app/`** — Python/FastAPI REST API. Tracks findings, manages remediation, and shares reports with stakeholders.
- **`notify/`** — Node.js/Express notification service. Dispatches webhook events when scan records are created or updated.

---

## Quick Start (Local Development)

### Python API

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Must run from inside app/ — modules use bare imports
cd app
uvicorn main:app --reload
```

Available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

Run tests from the **repo root**:

```bash
pytest tests/ -v
```

### Notification Service

```bash
cd notify
npm install
npm start
```

Available at `http://localhost:3001`. Run tests: `cd notify && npm test`

---

## Docker Build and Run

### Build

```bash
docker build -t vulntracker:latest .
```

### Run (local — dev-safe defaults for secrets)

```bash
docker run -p 8000:8000 vulntracker:latest
```

### Run (production — inject real secrets via environment variables)

```bash
docker run -p 8000:8000 \
  -e SECRET_KEY=your-strong-256bit-secret \
  -e DATABASE_URL=sqlite:///./data/vulntracker.db \
  -e NOTIFY_SERVICE_URL=http://notify-service:3001 \
  vulntracker:latest
```

The container satisfies all production requirements:

| Requirement | Implementation |
|-------------|----------------|
| Minimal pinned base image | `python:3.12-slim-bookworm` (multi-stage build) |
| Non-root user | Runs as `appuser` (created at build time, no shell) |
| HEALTHCHECK | Polls `/health` every 30s via Python stdlib `urllib` |
| No embedded secrets | All credentials read from `os.environ` at runtime |

### Verify the container is healthy

```bash
curl http://localhost:8000/health
# {"status": "ok", "service": "vulntracker-api"}
```

---

## Shared Report Link Feature

Two endpoints were added in Task 1:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/scans/{scan_id}/share` | Bearer token | Generate a 24-hour share token. Accepts optional `password` in the body. Returns `{"share_url": "..."}` |
| `GET` | `/share/{token}` | None (public) | Return scan data if the token is valid and not expired. Requires `?password=` query parameter if the link is password-protected. |

**Security properties of the implementation:**

- Tokens are generated with `secrets.token_urlsafe(32)` (256 bits of entropy)
- Passwords are stored as bcrypt hashes — never in plaintext
- Links expire after exactly 24 hours
- The public endpoint is rate-limited to **10 requests/minute per IP** to prevent brute-force password guessing

The `share_url` is constructed from the incoming request host so it works correctly behind reverse proxies.

---

## Kubernetes Deployment (Helm)

```bash
# Lint the chart
helm lint helm/

# 1. Create the Kubernetes Secret with real values (or use an external secrets operator)
kubectl create secret generic vulntracker-secret \
  --from-literal=SECRET_KEY=your-strong-key \
  --from-literal=DB_PASSWORD=your-db-password \
  --from-literal=ADMIN_API_KEY=your-api-key \
  -n vulntracker

# 2. Deploy
helm upgrade --install vulntracker helm/ \
  --namespace vulntracker \
  --create-namespace
```

Security properties of the Helm chart:

- Secrets sourced from `vulntracker-secret` Kubernetes Secret — **not hardcoded in manifests**
- `NetworkPolicy` restricts ingress to port 8000 only
- `SecurityContext`: `runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, all Linux capabilities dropped
- CPU and memory `requests`/`limits` defined
- Image referenced by **digest** (`sha256:...`) not just a mutable tag

---

## Security Scan Reports

| File | Tool | Scan Type |
|------|------|-----------|
| `reports/sast.sonarqube.json` | SonarQube | Static Application Security Testing (SAST) |
| `reports/sca.snyk.json` | Snyk | Software Composition Analysis (SCA) |
| `reports/container.trivy.json` | Trivy | Container image vulnerability scan |
| `reports/iac.checkov.json` | Checkov | Infrastructure-as-Code scan (Helm chart) |

See:
- `docs/findings.md` — prioritised findings with severity justification and business impact
- `docs/remediation-plan.md` — deferred findings with residual risk analysis
- `docs/executive-summary.md` — CISO-level summary

---

## Security Fixes Applied (Task 3)

Three critical/high findings were fixed in code:

| Finding | File Changed | Fix |
|---------|-------------|-----|
| SEC-01: SQL Injection | `app/database.py` | Replaced f-string SQL with SQLAlchemy `bindparams` — user input is never concatenated into the query |
| SEC-02: Hardcoded Secrets | `app/config.py` | All credentials now read from `os.environ.get()` with safe dev-only fallbacks |
| SEC-03: No Rate Limiting | `app/main.py` | Added `slowapi` IP-based rate limiter (10 req/min) on the public `/share/{token}` endpoint |

SEC-03 is in the Task 1 feature code, satisfying the requirement for at least one fix in newly written code.

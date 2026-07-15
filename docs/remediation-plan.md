# Remediation Plan

This document covers all security findings from docs/findings.md, stating which were remediated in code and explaining the residual risk, remediation effort, and compensating controls for those that were not.

---

## Findings Fully Remediated in Code

The following fixes are applied and visible in the git diff:

| Finding | Fix Applied |
|---------|-------------|
| **SEC-01** SQL Injection in search endpoint | Replaced f-string raw SQL with SQLAlchemy indparams in pp/database.py |
| **SEC-02** Hardcoded credentials in config.py | All secrets now read from environment variables via os.environ.get() |
| **SEC-03** No rate limiting on /share/{token} | Added IP-based rate limiting (10 req/min) via slowapi in pp/main.py |

---

## Findings NOT Remediated in Code

### SEC-04 — Insecure Service-to-Service Communication (unauthenticated HTTP)

**Finding:** The FastAPI service calls the notify microservice over plaintext, unauthenticated HTTP. An attacker with internal network access can send spoofed webhook payloads directly to the notify service.

**Residual Risk:** Medium. Exploitation requires being inside the Kubernetes cluster or internal network. The payload contains only non-sensitive metadata (scan ID, title, severity, owner username) — no tokens, passwords, or PII.

**Effort to remediate:**
1. Add a shared HMAC-SHA256 secret between services — approximately 2-3 hours of work.
2. Alternatively, deploy a service mesh (Istio/Linkerd) for mTLS — 1-2 days including cluster configuration.
3. Migrate notify service to HTTPS with TLS certificate validation — 1 day.

**Compensating controls currently in place:**
- The Helm NetworkPolicy restricts pod-level ingress so only the API pod can reach the notify service within the cluster.
- The notify service runs on ClusterIP (not NodePort/LoadBalancer), making it unreachable from outside the cluster.
- Payloads contain no credentials, tokens, or PII.

**Recommended next step:** Implement an X-Notify-Signature HMAC header in the next sprint (one-day task, no architectural dependencies).

---

### SEC-05 — Cryptographic Vulnerabilities in python-jose (CVE-2024-33663 / CVE-2024-33664)

**Finding:** python-jose==3.3.0 is vulnerable to algorithm confusion and JWE decompression bombs.

**Status: Effectively resolved.** The 
equirements.txt was already migrated from python-jose to pyjwt==2.13.0. The uth.py module uses pyjwt for all token operations. The vulnerable package is not installed.

No further code change is required. The finding is documented because it was present in the original starter code dependency history.

---

### SEC-06 — Out-of-Bounds Read in cryptography (CVE-2026-34180)

**Finding:** Earlier pinned version 38.0.1 of cryptography had an ASN.1 out-of-bounds read.

**Status: Effectively resolved.** 
equirements.txt now pins cryptography>=46.0.5, which incorporates the patch. The vulnerable version cannot be installed.

**Residual exposure:** A newly disclosed vulnerability in a version above 46.0.5 would not be caught without a running dependency scanner. **Compensating control:** The Snyk SCA job in CI runs on every push and would flag new CVEs before a release.

---

### SEC-07 — Race Condition in nyio (SNYK-PYTHON-ANYIO-7361842)

**Finding:** nyio==3.7.1 had a race condition in event loop initialization.

**Status: Effectively resolved.** 
equirements.txt is pinned to nyio==4.4.0, which resolves this issue.

---

### SEC-08 — OS Vulnerabilities in Base Container Image

**Finding:** The Debian Bookworm base image contains outdated OS packages with known CVEs (reported by Trivy — approximately 290 findings, several rated CRITICAL/HIGH).

**Residual Risk:** Medium. Most vulnerable packages are not directly invoked by the application. The attack path requires first achieving code execution inside the container.

**Effort to remediate fully:**
1. Automate weekly image rebuilds in CI to pull Debian security updates — 1 day.
2. Switch to a distroless base image (gcr.io/distroless/python3) to eliminate OS tooling entirely — 0.5-1 day.
3. Pin the base image to an immutable digest and use Renovate/Dependabot to auto-update — 1 day.

**Compensating controls currently in place:**
- Container runs as **non-root user** (UID 10001), limiting blast radius of any exploit.
- Kubernetes SecurityContext enforces 
eadOnlyRootFilesystem: true, llowPrivilegeEscalation: false, and drops all Linux capabilities.
- Helm NetworkPolicy prevents the container from initiating arbitrary outbound connections.
- Trivy container scan in CI alerts on newly disclosed CRITICAL/HIGH CVEs before release.

**Recommended next step:** Pin the FROM line to a digest and add a scheduled weekly CI rebuild so OS patches are applied automatically.

---

## Summary Table

| Finding | Status | Residual Risk | Priority |
|---------|--------|---------------|----------|
| SEC-01 SQL Injection | Fixed in code | None | Done |
| SEC-02 Hardcoded Secrets | Fixed in code | None | Done |
| SEC-03 No Rate Limiting | Fixed in code | None | Done |
| SEC-04 Unauthenticated HTTP | Deferred | Medium | Next sprint |
| SEC-05 python-jose CVEs | Resolved (package replaced) | None | Done |
| SEC-06 cryptography CVE | Resolved (version pinned) | None | Done |
| SEC-07 anyio race condition | Resolved (version pinned) | None | Done |
| SEC-08 OS container CVEs | Deferred | Medium | Next sprint |

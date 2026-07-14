# Security Findings Report

This document details the security vulnerabilities identified in the **VulnTracker** application. Findings are compiled from automated tools (SonarQube SAST, Snyk SCA, and Trivy Container scans) as well as a manual secure code review of the source files.

---

## Security Findings Summary Table

| Finding ID | Vulnerability / Finding Name | Tool & Scan Type | Severity (Assessed) | Severity Justification | Business Impact | Location |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | SQL Injection in Scan Search Endpoint | Manual Review | **Critical** | User input from the query parameter `q` is directly interpolated into a raw SQL statement in `database.py` without parameterization or validation. Allows execution of arbitrary SQLite queries. | Attackers can bypass authorization checks, query database tables, dump user credentials/emails/hashes, or delete all scan data. | Starter Code (`app/database.py`) |
| **SEC-02** | Hardcoded Secrets and Key Material | Manual Review | **High** | Secret key (`SECRET_KEY`), database password (`DB_PASSWORD`), and notify service key are hardcoded in `config.py`. If source code is compromised (e.g., public repo), these are exposed. | Allows attackers to mint valid JWT authentication tokens (impersonating any user) and gain direct database access. | Starter Code (`app/config.py`) |
| **SEC-03** | Lack of Rate Limiting on Password-Protected Shared Links | Manual Review | **Medium** | The `/share/{token}` endpoint verifies passwords for protected links but does not implement rate limiting or brute-force lockouts. | Weak passwords on shared links can be brute-forced, exposing sensitive vulnerability details of specific scan results to unauthorized parties. | New Feature (`app/main.py`) |
| **SEC-04** | Insecure Service-to-Service Communication | Manual Review | **Medium** | Communication between the Python API and the Node.js notification service uses unauthenticated/unsigned HTTP requests. | A network-based attacker can send spoofed webhook events directly to `/notify`, disrupting integrated notification workflows or logging false events. | Starter Code (`app/main.py` -> `notify/`) |
| **SEC-05** | Cryptographic Vulnerabilities in `python-jose` (CVE-2024-33663 / CVE-2024-33664) | Dependency Scan (Snyk SCA) | **High** | Package version `3.3.0` is vulnerable to algorithm confusion (improper signature verification) and compression bomb attacks (DoS). | An attacker can cause service crashes (DoS) using a crafted token or bypass signature validation depending on JWT configurations. | Starter Code (`requirements.txt`) |
| **SEC-06** | Out-of-Bounds Read in `cryptography` dependency (CVE-2026-34180) | Dependency Scan (Snyk SCA) | **High** | Pinned version `38.0.1` has a vulnerability in the ASN.1 decoder. Maliciously crafted input can read out-of-bounds memory. | Processing arbitrary stakeholder certificates or tokens can trigger server crashes, leading to Denial of Service (DoS). | Starter Code (`requirements.txt`) |
| **SEC-07** | Race Condition in `anyio` package (SNYK-PYTHON-ANYIO-7361842) | Dependency Scan (Snyk SCA) | **High** | Event loop creation in `anyio` version `3.7.1` is prone to race conditions when concurrent threads initialize event loops. | High concurrent traffic could trigger sudden worker thread crashes, resulting in service denial of service or slow response times. | Starter Code (`requirements.txt`) |
| **SEC-08** | OS Vulnerabilities in Base Container Image (e.g., CVE-2026-33845) | Container Scan (Trivy) | **Medium** | Over 290 vulnerabilities found in base Debian packages (such as `libgnutls30`), including several marked CRITICAL/HIGH. | Exploitation of OS library flaws could allow a container compromise or host sandbox evasion if a remote code execution vulnerability is chained. | Starter Code (`Dockerfile`) |

---

## Detailed Assessment of Findings

### SEC-01: SQL Injection in Scan Search Endpoint
*   **Detector:** Manual Review (Missed by SonarQube due to raw text wrapping).
*   **Technical Details:** 
    The search logic in `database.py` constructs a raw SQL query using f-string interpolation:
    ```python
    sql = (
        f"SELECT id, title, description, severity, status, cve_id, "
        f"affected_component, owner_id, created_at FROM scan_results "
        f"WHERE title LIKE '%{query}%' OR description LIKE '%{query}%' "
        f"OR cve_id LIKE '%{query}%'"
    )
    result = db.execute(text(sql))
    ```
    This allows an attacker to supply a payload like `' OR 1=1 --` in the `q` query parameter of the `/scans/search` endpoint.
*   **Business Impact:** This vulnerability completely breaks the authorization boundary of the multi-user environment. An auditor or regular user can access scan results they do not own, delete scan data, or run SQLite helper functions to read local file structures.

### SEC-02: Hardcoded Secrets and Key Material
*   **Detector:** Manual Review.
*   **Technical Details:** 
    `config.py` contains hardcoded plaintext strings:
    ```python
    SECRET_KEY = "v3ry-s3cr3t-jwt-k3y-do-not-share"
    DB_PASSWORD = "Tr@cker2024!"
    ADMIN_API_KEY = "sk-vt-prod-8f3a2b1c9d4e5f6a7b8c9d0e1f2a3b4c"
    ```
*   **Business Impact:** Any system administrator, developer, or malicious actor who gains read access to the repository has complete authority over the application. With the `SECRET_KEY`, they can sign JWTs as any user, bypassing authentication controls entirely.

### SEC-03: Lack of Rate Limiting on Shared Links
*   **Detector:** Manual Review.
*   **Technical Details:** 
    The endpoint `/share/{token}` retrieves a report and requests a password if the link is password-protected. However, there is no delay, locking, or logging mechanism on failed attempts.
*   **Business Impact:** An attacker can repeatedly submit candidate passwords via automated scripting to guess the password. If a customer or auditor uses a weak or standard password, their shared report can be compromised within minutes.

### SEC-04: Insecure Service-to-Service Communication
*   **Detector:** Manual Review.
*   **Technical Details:** 
    The FastAPI API invokes the notify microservice by making a POST request to `f"{NOTIFY_SERVICE_URL}/notify"` with raw payloads. No signature, bearer authentication, or TLS validation is enforced by the receiver.
*   **Business Impact:** If an attacker gains internal network access, they can dispatch mock vulnerability notifications to endpoints, causing organizational disruption, triggering false alerts, or intercepting sensitive data contained in payload schemas.

### SEC-05: Cryptographic Vulnerabilities in `python-jose`
*   **Detector:** Snyk SCA.
*   **Technical Details:** 
    Package version `3.3.0` was vulnerable to algorithmic confusion where ECDSA keys could be misparsed, allowing signature bypass. Additionally, JWE token decompression had no limits (data amplification/decompression bomb).
*   **Business Impact:** Attackers could exhaust system resources (CPU/RAM) using malformed tokens, rendering VulnTracker unavailable.

### SEC-06: Out-of-Bounds Read in `cryptography`
*   **Detector:** Snyk SCA (CVE-2026-34180).
*   **Technical Details:** 
    Out-of-bounds read in the ASN.1 decoder inside OpenSSL bindings.
*   **Business Impact:** Causes a service crash (DoS) if certificates or signatures provided by third parties (e.g. during auditor connection setup) are malicious.

### SEC-07: Race Condition in `anyio`
*   **Detector:** Snyk SCA (SNYK-PYTHON-ANYIO-7361842).
*   **Technical Details:** 
    Multiple event loops simultaneously attempting to invoke `_eventloop.get_asynclib()` can cause thread collision and application crashes.
*   **Business Impact:** Under moderate to high web request traffic, workers can crash randomly, resulting in HTTP 502/504 gateway timeouts.

### SEC-08: Container OS Package Vulnerabilities
*   **Detector:** Trivy Container Image Scan.
*   **Technical Details:** 
    The base Debian Bookworm image contains several outdated dependencies like `libgnutls30` and `bsdutils`.
*   **Business Impact:** Increases the attack surface. If an attacker manages to execute code in the container context (e.g., via a Python remote execution flaw), outdated system libraries make privilege escalation or container escape significantly easier.

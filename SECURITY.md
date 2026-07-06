# Security Policy

OneDrop is designed specifically for transferring secrets and credentials on a trusted LAN or VPN. This document describes what it protects against, what it doesn't, how to report a vulnerability, and specific risks in the implementation you should understand before deploying it for anything sensitive.

---

## Supported Versions

Only the current release receives security patches. This is a single-maintainer project with no LTS branches.

| Version                     | Supported                 |
| --------------------------- | ------------------------- |
| Latest (`main`)             | ✅ Yes                    |
| Any previous tagged release | ❌ No - upgrade to latest |

---

## Reporting a Vulnerability

**Do not open a public issue for security reports.**

Open a private security advisory on GitHub: **Security → Advisories → "Report a vulnerability"**.

If you cannot use GitHub advisories, email **security@example.com** with:

- A description of the vulnerability and what an attacker could do
- Steps to reproduce
- The version of OneDrop you tested against
- Any proof-of-concept code (even rough pseudocode helps)

**Response timeline:**

| Step                                 | Target                                          |
| ------------------------------------ | ----------------------------------------------- |
| Initial acknowledgement              | Within 48 hours                                 |
| Severity triage and decision         | Within 5 business days                          |
| Fix released or workaround published | Within 30 days for critical, 90 days for others |
| CVE assignment (if warranted)        | Coordinated with release                        |

We will credit reporters in the changelog unless you prefer to remain anonymous.

---

## What OneDrop Protects Against

- **Passive eavesdropping on the LAN.** TLS 1.2+ encrypts all traffic between server and client.
- **Unauthorized access without the token.** The capability URL embeds a 32-byte cryptographically random token checked with `hmac.compare_digest` (constant-time), so guessing or timing the token is not feasible.
- **Link reuse after download.** By default, the link returns HTTP 410 Gone after one successful download and the server shuts down.
- **Path traversal.** The URL router accepts exactly three valid structures (`/t/{token}`, `/t/{token}/{filename}`, `/t/{token}/rootCA.pem`). Any other path, including `../../etc/passwd`-style requests, is rejected before touching the filesystem.
- **Token leakage into logs.** The audit logger always redacts the capability token from path strings before writing to disk.
- **File integrity tampering.** SHA-256 of the file is computed and displayed at startup and on the landing page for independent verification by the recipient.

---

## Threat Model & Known Limitations

### 1. The capability token lives in the URL

The token is embedded in the URL (`/t/{token}/filename`). This is convenient but carries inherent risk:

- **Browser history, bookmarks, and server access logs** on any proxy or load balancer between sender and recipient will capture the full URL, including the token.
- **Referrer headers** - if the recipient clicks a link from the landing page to an external resource, the full URL (including the token) may be sent as the `Referer` header.
- **URL sharing** - if the recipient forwards the URL to anyone (e.g., pastes it into Slack), the link works for them too until the download limit is reached.

**Mitigations:**

- Use `--max-downloads 1` (the default). Even if the URL leaks, it stops working after the first download.
- Share the URL over an encrypted channel (Signal, an encrypted email, verbally).
- After the server shuts down, the token is gone - there's nothing to rotate.

### 2. Self-signed TLS does not authenticate the server by default

Unless you supply a certificate from a CA your recipients already trust, OneDrop auto-generates a self-signed certificate. Clients will see a browser warning, and a network attacker who can intercept traffic could substitute their own self-signed cert - a MITM attack that TLS alone does not prevent when there's no trusted anchor.

**The fingerprint mechanism partially addresses this:** OneDrop prints the certificate's SHA-256 fingerprint at startup and displays it on the landing page. If the recipient verifies this fingerprint out-of-band before clicking Download, they can detect a MITM. But this requires an active step that most recipients will skip.

**Mitigations:**

- Use `mkcert` to generate a cert your devices already trust, and follow the Root CA installation steps for mobile devices.
- For high-stakes transfers, read the `Cert SHA256` value aloud to the recipient or send it separately, and ask them to verify it in their browser's certificate viewer before downloading.
- If your organisation has an internal CA, issue a cert from it.

### 3. No rate limiting on failed token validation attempts

When a request arrives with a missing or wrong token, OneDrop responds with HTTP 404 (deliberately identical to a "not found" response - this avoids leaking whether a valid route exists). However, it does **not** implement any rate limiting, IP-based backoff, or lockout on failed attempts.

In practice, guessing a 32-byte `secrets.token_urlsafe` token by brute force is computationally infeasible. The risk is not brute force but rather:

- An attacker who already knows the URL structure (e.g., from monitoring network traffic) and wants to probe for variations.
- Automated scanners on the LAN that stumble onto the port.

**Mitigations:**

- Bind to a specific LAN interface with `--bind <ip>` rather than letting the OS pick. This limits which machines can even reach the server.
- Keep `--max-downloads` at 1. The server exits as soon as the file is downloaded, so the exposure window is minimal.
- Run on a non-standard port if port 443 is scanned by internal tooling.

### 4. Broken pipe / dropped connection consumes a download slot

The download counter is incremented by `DownloadLimiter.try_consume()` **before** the file is streamed. If the recipient disconnects mid-download (network drop, closed browser tab), the slot is consumed even though they didn't receive the file. With `--max-downloads 1`, this means the link is dead even though the transfer failed.

**Mitigations:**

- If a download fails partway, restart OneDrop with `--max-downloads 1` again. The token will be different, so share the new URL.
- Use `--max-downloads 2` on flaky connections so one retry is available.

### 5. Template rendering with `str.format()` on untrusted filenames

The landing page HTML is rendered by calling `str.format()` on an HTML template, injecting the filename directly. A filename containing a literal `{` or `}` character will cause a `KeyError` and a 500-equivalent crash when the landing page is requested.

This is a denial-of-service risk (server crashes before any download happens), not an injection risk - the `str.format()` substitution happens on named keys, and the template does not expose any Python attribute access paths. However, it means sharing a file named e.g. `config_{env}.json` will break the landing page.

**Current status:** This is a known issue in the codebase. A workaround is to rename the file before sharing, or use `curl` to download directly without loading the landing page.

---

## Security Best Practices for Deployment

**Do:**

- Always verify the `Cert SHA256` fingerprint with your recipient out-of-band before they click Download, especially for production secrets.
- Use `mkcert` for a locally-trusted certificate. It takes two minutes and eliminates the browser warning entirely.
- Bind to a specific interface (`ONEDROP_BIND=192.168.1.x` or `--bind <ip>`) to limit which machines on the network can reach the server.
- Review `access_audit.log` after every session. It records every request by IP, path, and outcome. Unexpected IPs in the log mean someone else on the network found your URL.
- Delete or overwrite the file you shared immediately after confirming the recipient has it. OneDrop does not delete the source file.
- Rotate any credential that was transmitted. Even a successful, verified transfer should be treated as an opportunity to issue a fresh credential to the recipient, not to share a long-lived one.

**Don't:**

- Run OneDrop on a machine accessible from the internet. It is designed exclusively for LAN/VPN use. Binding to `0.0.0.0` on a machine with a public interface exposes the server to the internet.
- Share the capability URL over unencrypted channels (plain email, SMS, Slack DM without encryption). Use Signal, an encrypted messaging channel, or share it verbally.
- Share sensitive files with `--max-downloads` set high "just in case." Every additional slot is additional risk. If the recipient needs to re-download, restart the server.
- Assume the audit log is tamper-proof. It is an append-only file on disk with standard filesystem permissions. Anyone with write access to the machine can modify or delete it.

---

## What This Tool Is Not

- **Not a replacement for a secrets manager.** Use Vault, AWS Secrets Manager, or similar for persistent, audited, role-based credential distribution. OneDrop is for the one-time bootstrap problem: getting the first credential onto a new machine.
- **Not suitable for regulated data without additional controls.** If you're handling PHI, PII, PCI data, or anything subject to compliance requirements, OneDrop does not provide the access controls, retention policies, or audit infrastructure those frameworks require.
- **Not a file server.** The hard cap of 25 downloads and the self-destruct behaviour are intentional. This tool should never be left running unattended.

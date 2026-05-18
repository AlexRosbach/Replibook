# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 1.x | ✅ |

## Reporting a Vulnerability

**Please do not report security vulnerabilities as public GitHub Issues.**

Report security issues privately via [GitHub Security Advisories](../../security/advisories/new).

Include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix (optional)

You will receive a response within 72 hours.

## Scope

**In scope:**
- Command injection via scanner inputs
- Privilege escalation through the tool itself
- Insecure handling of environment variables or secrets read during Docker scanning

**Out of scope:**
- Security of the generated Ansible playbooks (responsibility of the operator)
- Vulnerabilities in third-party dependencies (report upstream)
- Issues on unsupported versions

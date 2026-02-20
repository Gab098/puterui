# Security Audit
> Source code security auditing and vulnerability assessment

## Code Review for Security

### Injection Vulnerabilities
- SQL: String concatenation in queries, missing parameterized statements
- Command injection: os.system(), subprocess with shell=True, exec()
- Template injection: User input in template rendering
- LDAP/XPath: Unsanitized input in directory queries

### Authentication & Session
- Hardcoded credentials, API keys, tokens in source
- Weak password hashing (MD5, SHA1, no salt)
- Missing rate limiting on auth endpoints
- Session tokens with insufficient entropy
- Missing CSRF protection on state-changing operations

### Data Exposure
- Sensitive data in logs (passwords, tokens, PII)
- Verbose error messages leaking stack traces
- Debug endpoints left enabled
- Missing encryption for data at rest/transit
- Secrets in version control history

### Access Control
- Missing authorization checks on endpoints
- IDOR: Object references without ownership validation
- Privilege escalation: Role checks missing or bypassable
- Path traversal: File operations with user-controlled paths

### Dependency Security
- Known vulnerable dependencies (npm audit, pip-audit, snyk)
- Outdated packages with security patches available
- Typosquatting risk in package names
- Unnecessary dependencies increasing attack surface

### Configuration
- CORS: Overly permissive origins, credentials with wildcard
- Security headers: Missing CSP, HSTS, X-Frame-Options
- TLS: Weak cipher suites, outdated TLS versions
- Default configurations left unchanged

## Audit Methodology
1. Map the attack surface (endpoints, inputs, integrations)
2. Trace data flow from input to output
3. Check each input point for injection
4. Verify authentication and authorization at every layer
5. Review cryptographic implementations
6. Check dependency versions against vulnerability databases
7. Review configuration files and deployment settings
8. Produce findings with severity, evidence, and remediation

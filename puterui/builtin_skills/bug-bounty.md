# Bug Bounty
> Systematic bug bounty hunting methodology and vulnerability discovery

## Recon Phase
1. **Subdomain enumeration**: Use tools like subfinder, amass, assetfinder
2. **Port scanning**: nmap for service discovery
3. **Technology fingerprinting**: whatweb, wappalyzer, builtwith
4. **Directory/file bruteforcing**: ffuf, gobuster, dirsearch
5. **JavaScript analysis**: Extract endpoints, secrets, API keys from JS files
6. **Wayback Machine**: Check historical URLs via waybackurls, gau
7. **Google dorking**: site:target.com filetype:pdf, inurl:admin, etc.

## Vulnerability Testing
1. **OWASP Top 10**: Test for each category systematically
2. **Injection**: SQL, NoSQL, LDAP, XPath, OS command, template injection
3. **XSS**: Reflected, stored, DOM-based -- test all input points
4. **SSRF**: Internal network access, cloud metadata endpoints
5. **IDOR**: Test object references with different user contexts
6. **Auth bypass**: JWT manipulation, session fixation, privilege escalation
7. **File upload**: Extension bypass, content-type manipulation, polyglots
8. **Race conditions**: TOCTOU, parallel request exploitation
9. **Business logic**: Price manipulation, coupon abuse, workflow bypass

## Reporting
- Clear title describing the vulnerability
- Step-by-step reproduction instructions
- Impact assessment (CVSS if applicable)
- Proof of concept (screenshots, HTTP requests)
- Suggested remediation
- Do NOT access data beyond what is needed to prove the vulnerability

## Ethics
- Only test in-scope targets with explicit authorization
- Follow responsible disclosure practices
- Never access, modify, or exfiltrate real user data
- Report findings through proper channels

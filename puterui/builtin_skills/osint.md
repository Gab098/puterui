# OSINT
> Open Source Intelligence gathering techniques and methodology

## Information Gathering Framework

### Domain Intelligence
1. **WHOIS**: Domain registration, registrar, nameservers, dates
2. **DNS records**: A, AAAA, MX, TXT, CNAME, NS, SOA records
3. **Reverse DNS**: PTR records, IP-to-hostname mapping
4. **Certificate transparency**: crt.sh, censys for SSL cert history
5. **Subdomains**: Passive (SecurityTrails, VirusTotal) and active enumeration

### Infrastructure Mapping
1. **IP ranges**: ASN lookup, BGP routing info, CIDR blocks
2. **Cloud provider detection**: AWS, GCP, Azure IP ranges
3. **CDN detection**: Cloudflare, Akamai, Fastly origin discovery
4. **Hosting**: Shared hosting neighbors, VPS provider identification
5. **Historical data**: Wayback Machine, DNS history, archive.org

### Web Application OSINT
1. **Technology stack**: Server headers, cookies, HTML meta tags
2. **CMS detection**: WordPress, Drupal, Joomla version fingerprinting
3. **JavaScript libraries**: Frontend framework identification
4. **API discovery**: Swagger/OpenAPI docs, GraphQL introspection
5. **Robots.txt / sitemap.xml**: Hidden paths and structure

### People and Organization
1. **Email patterns**: firstname.lastname@domain format discovery
2. **LinkedIn**: Employee roles, tech stack mentions in job postings
3. **GitHub/GitLab**: Public repos, commit emails, leaked credentials
4. **Social media**: Twitter, Reddit mentions of internal tools/stack
5. **Paste sites**: Pastebin, GitHub Gists for leaked data

### Network Intelligence
1. **Shodan/Censys**: Exposed services, banners, vulnerabilities
2. **Port scanning**: Service version detection
3. **SSL/TLS analysis**: Certificate details, supported ciphers
4. **Email security**: SPF, DKIM, DMARC records

## Tools Reference
- **DNS**: dig, nslookup, host, dnsrecon, dnsenum
- **Subdomains**: subfinder, amass, assetfinder, knockpy
- **Web**: whatweb, httpx, nuclei, waybackurls, gau
- **Network**: nmap, masscan, shodan CLI, censys CLI
- **Metadata**: exiftool, metagoofil, foca

## Ethics
- Only gather publicly available information
- Respect privacy laws and regulations
- Do not access systems without authorization
- Document your methodology for reproducibility

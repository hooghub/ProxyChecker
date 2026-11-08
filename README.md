# ProxyChecker

VPS terminal HTTP/HTTPS proxy checker. Supports Alpine Linux, Debian and Ubuntu.

## Usage

After uploading these files to the GitHub `main` branch:

```bash
bash <(curl -Ls https://raw.githubusercontent.com/hooghub/ProxyChecker/main/ipchecker.sh)
```

Run as root. The bootstrap script installs dependencies and downloads `IPcheck.py` to `/opt/ipchecker`.

When prompted, enter the path to a TXT file already uploaded to the VPS. Use one proxy per line:

```text

http://user:password@203.0.113.00
```

Supports HTTP and HTTPS proxies only. Maximum 500 unique entries, 5 concurrent checks, 15-second timeout.

The terminal shows the proxy endpoint being checked and its detected exit IP. `results.txt` is written to the current working directory and does not include source proxy endpoints or credentials.

Geo lookup sends detected exit IP addresses to ip-api.com over HTTP. Country and network type may be Unknown; Residential/ISP is not guessed. Only test proxy endpoints you are authorized to use.

On a minimal Alpine installation, Bash must exist before using process substitution. If needed, first run `apk add --no-cache bash`.

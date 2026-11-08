#!/usr/bin/env python3
import os
import socket
import sys
import threading
import time
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

MAX_PROXIES = 500
WORKERS = 5
TIMEOUT = 15
TCP_TIMEOUT = 5
TEST_URL = "https://api.ipify.org?format=json"
GEO_URL = "http://ip-api.com/json/{ip}?fields=status,country,hosting,mobile"

_geo_cache = {}
_geo_lock = threading.Lock()


def lookup_geo_ip(exit_ip):
    """查单个出口 IP 的国家和网络类型，相同出口 IP 只查一次。"""
    with _geo_lock:
        if exit_ip in _geo_cache:
            return _geo_cache[exit_ip]
    info = {"country": "Unknown", "ip_type": "Unknown"}
    try:
        response = requests.get(GEO_URL.format(ip=exit_ip), timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            if data.get("hosting") is True:
                ip_type = "Datacenter"
            elif data.get("mobile") is True:
                ip_type = "Mobile"
            else:
                ip_type = "Unknown"
            info = {
                "country": data.get("country") or "Unknown",
                "ip_type": ip_type,
            }
    except Exception:
        pass
    with _geo_lock:
        _geo_cache[exit_ip] = info
    return info


def parse_proxy(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "://" not in line:
        line = "http://" + line
    try:
        parsed = urlsplit(line)
        if parsed.scheme.lower() not in ("http", "https"):
            return None
        if not parsed.hostname or parsed.port is None:
            return None
        return line
    except (ValueError, TypeError):
        return None


def safe_label(proxy):
    parsed = urlsplit(proxy)
    host = parsed.hostname or "unknown"
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"{host}:{parsed.port}"


def check_proxy(index, proxy, total):
    print(f"[{index}/{total}] 检测中: {safe_label(proxy)}", flush=True)
    parsed = urlsplit(proxy)
    host, port = parsed.hostname, parsed.port

    # 第一步：TCP 直连，看端口通不通
    tcp_started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=TCP_TIMEOUT):
            pass
        tcp_latency = round((time.monotonic() - tcp_started) * 1000)
    except Exception:
        print(f"[{index}/{total}] 离线 | TCP 连接失败", flush=True)
        return {
            "exit_ip": "",
            "latency": 0,
            "status": "离线",
            "country": "Unknown",
            "ip_type": "Unknown",
        }

    # 第二步：TCP 通了，再走代理发 HTTP 请求拿出口 IP 和地区
    started = time.monotonic()

    try:
        response = requests.get(
            TEST_URL,
            proxies={"http": proxy, "https": proxy},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        exit_ip = response.json().get("ip")
        if not exit_ip:
            raise ValueError("No exit IP returned")

        latency = round((time.monotonic() - started) * 1000)
        geo = lookup_geo_ip(exit_ip)
        print(
            f"[{index}/{total}] 在线 | 代理: {safe_label(proxy)} | "
            f"出口 IP: {exit_ip} | {geo['country']} | "
            f"{geo['ip_type']} | TCP {tcp_latency} ms / 总 {latency} ms",
            flush=True,
        )
        return {
            "exit_ip": exit_ip,
            "latency": latency,
            "status": "在线",
            "country": geo["country"],
            "ip_type": geo["ip_type"],
        }
    except Exception:
        print(f"[{index}/{total}] 离线 | TCP 通但代理请求失败", flush=True)
        return {
            "exit_ip": "",
            "latency": 0,
            "status": "离线",
            "country": "Unknown",
            "ip_type": "Unknown",
        }


def main():
    if len(sys.argv) != 2:
        print("用法: python3 IPcheck.py /path/to/proxies.txt")
        return 2

    input_file = os.path.abspath(os.path.expanduser(sys.argv[1]))
    if not os.path.isfile(input_file):
        print(f"[错误] TXT 文件不存在：{input_file}")
        return 2

    with open(input_file, "r", encoding="utf-8-sig") as handle:
        proxies = [parse_proxy(line) for line in handle]

    proxies = list(dict.fromkeys(proxy for proxy in proxies if proxy))
    if not proxies:
        print("[错误] TXT 中没有有效的 HTTP/HTTPS 代理")
        return 2

    if len(proxies) > MAX_PROXIES:
        print(f"[提示] 超过 {MAX_PROXIES} 条，只检测前 {MAX_PROXIES} 条")
        proxies = proxies[:MAX_PROXIES]

    total = len(proxies)
    print("======================================")
    print("        HTTP Proxy Checker")
    print("======================================")
    print(f"代理数量：{total}")
    print(f"并发数量：{WORKERS}")
    print(f"超时时间：{TIMEOUT} 秒")
    print("======================================\n")

    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [
            pool.submit(check_proxy, index, proxy, total)
            for index, proxy in enumerate(proxies, 1)
        ]
        for future in as_completed(futures):
            results.append(future.result())

    online = [item for item in results if item["status"] == "在线"]
    output_file = os.path.abspath("results.txt")
    with open(output_file, "w", encoding="utf-8") as handle:
        handle.write("HTTP Proxy Checker Results\n")
        handle.write("==========================\n")
        handle.write(f"Total: {total}\n")
        handle.write(f"Online: {len(online)}\n")
        handle.write(f"Offline: {total - len(online)}\n\n")
        for item in sorted(results, key=lambda row: row["latency"] or 10**9):
            if item["status"] == "在线":
                handle.write(
                    f'{item["country"]} | {item["ip_type"]} | '
                    f'{item["latency"]} ms\n'
                )

    print("\n======================================")
    print("检测完成")
    print(f"总数：{total}")
    print(f"在线：{len(online)}")
    print(f"离线：{total - len(online)}")
    print(f"结果文件：{output_file}")
    print("注意：results.txt 不包含原始代理地址和账号密码")
    print("======================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

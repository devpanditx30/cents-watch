#!/usr/bin/env python3
import re, json, os, html, urllib.request

URL = "https://testcisia.it/calendario.php?tolc=cents&l=gb&lingua=inglese"
TOPIC = os.environ.get("NTFY_TOPIC", "")
STATE_FILE = "cents_state.json"
FILTER = []


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def rows(page):
    out = []
    for tr in re.findall(r"<tr.*?</tr>", page, flags=re.S | re.I):
        cells = re.findall(r"<t[dh].*?>(.*?)</t[dh]>", tr, flags=re.S | re.I)
        cells = [html.unescape(re.sub(r"<[^>]+>", " ", c)) for c in cells]
        cells = [re.sub(r"\s+", " ", c).strip() for c in cells]
        line = " | ".join(c for c in cells if c)
        if line:
            out.append(line)
    return out


def is_open(line):
    u = line.upper()
    return "AVAILABLE" in u and "NOT LONGER" not in u and "CLOSED" not in u


def notify(title, msg):
    if not TOPIC:
        print("NTFY_TOPIC not set:", title, msg)
        return
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}", data=msg.encode("utf-8"),
        headers={"Title": title, "Priority": "urgent", "Tags": "rotating_light", "Click": URL})
    urllib.request.urlopen(req, timeout=30)


MAX_ALERTS = 10


def key(line):
    return " | ".join(c for c in line.split(" | ") if not c.strip().isdigit())


def main():
    raw = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}
    counts = {key(x): MAX_ALERTS for x in raw} if isinstance(raw, list) else raw
    lines = [l for l in rows(fetch()) if "CENT" in l.upper()]
    if FILTER:
        lines = [l for l in lines if any(f.lower() in l.lower() for f in FILTER)]
    open_now = {key(l): l for l in lines if is_open(l)}
    due = {k: l for k, l in open_now.items() if counts.get(k, 0) < MAX_ALERTS}
    print(f"{len(lines)} rows, {len(due)} to alert")
    for k, l in due.items():
        n = counts.get(k, 0) + 1
        notify(f"CEnT-S slot open! ({n}/{MAX_ALERTS})", l)
    new_counts = {k: counts.get(k, 0) + (1 if k in due else 0) for k in open_now}
    json.dump(new_counts, open(STATE_FILE, "w"))


if __name__ == "__main__":
    main()

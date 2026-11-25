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


def main():
    seen = set(json.load(open(STATE_FILE))) if os.path.exists(STATE_FILE) else set()
    lines = [l for l in rows(fetch()) if "CENT" in l.upper()]
    if FILTER:
        lines = [l for l in lines if any(f.lower() in l.lower() for f in FILTER)]
    fresh = [l for l in lines if is_open(l) and l not in seen]
    print(f"{len(lines)} rows, {len(fresh)} new open")
    if fresh:
        notify("CEnT-S slot open!", "\n".join(fresh[:5]))
        seen.update(fresh)
        json.dump(sorted(seen), open(STATE_FILE, "w"))


if __name__ == "__main__":
    main()

"""Copy the 'Pendency Data' Google Sheet tabs into data/*.csv for the dashboard.

Runs on GitHub Actions. The dashboard first reads Google directly; when a
browser or network blocks that, it reads these copies instead.
"""
import csv, io, json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

SHEET_ID = "1ftO6W5nTsEJjyxqQEtqBYEUJ7m6e2uDOW86S8PiPZxI"
TABS = {
    "RPC Raw Material": lambda head: "in qty" in head,
    "Projection Qty": lambda head: "req" in head and "in qty" not in head,
    "Non-Usable Data": lambda head: "qty" in head and "in qty" not in head,
}
OUT = os.path.join(os.path.dirname(__file__), "..", "data")


def fetch(tab):
    url = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&headers=1&sheet="
           + urllib.parse.quote(tab))
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "rpc-tracker-sync"}), timeout=60) as r:
        text = r.read().decode("utf-8")
    if text.lstrip().startswith("<") or "google.visualization" in text[:200]:
        raise RuntimeError(f"tab '{tab}': sheet is not shared for viewing")
    return text


def main():
    os.makedirs(OUT, exist_ok=True)
    changed = False
    for tab, looks_right in TABS.items():
        try:
            text = fetch(tab)
        except Exception as e:  # optional tab (non-usable) may be missing
            if tab == "Non-Usable Data":
                print(f"skip {tab}: {e}")
                continue
            sys.exit(f"Could not read '{tab}': {e}")
        head = next(csv.reader(io.StringIO(text)), [])
        if not looks_right(",".join(head).lower()):
            if tab == "Non-Usable Data":
                print(f"skip {tab}: unexpected columns {head}")
                continue
            sys.exit(f"'{tab}' has unexpected columns: {head}")
        path = os.path.join(OUT, f"{tab}.csv")
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old != text:
            open(path, "w", encoding="utf-8").write(text)
            changed = True
            print(f"updated {tab} ({text.count(chr(10))} lines)")
    if changed or not os.path.exists(os.path.join(OUT, "meta.json")):
        json.dump({"copiedAt": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                  open(os.path.join(OUT, "meta.json"), "w"))
    print("changed" if changed else "no change")


if __name__ == "__main__":
    main()

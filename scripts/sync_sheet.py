"""Copy the 'Pendency Data' Google Sheet tabs into data/*.csv for the dashboard.

Runs on GitHub Actions. Uses Google's full Excel export (keeps every date,
unlike the quick CSV link, which blanks dates when a column mixes formats).
Falls back to the quick CSV link if the export is unavailable.
"""
import csv, io, json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, date

SHEET_ID = "1ftO6W5nTsEJjyxqQEtqBYEUJ7m6e2uDOW86S8PiPZxI"
TABS = {
    "RPC Raw Material": lambda head: "in qty" in head,
    "Projection Qty": lambda head: "req" in head and "in qty" not in head,
    "Non-Usable Data": lambda head: "qty" in head and "in qty" not in head,
    "MR": lambda head: "mr number" in head,
}
OPTIONAL = {"Non-Usable Data", "MR"}
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
UA = {"User-Agent": "rpc-tracker-sync"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
        return r.read()


def cell(v, col=""):
    if col == "month" and isinstance(v, (datetime, date)):
        return v.strftime("%b-%y")  # shown as Nov-26 in the sheet
    if v is None:
        return ""
    if isinstance(v, datetime) or isinstance(v, date):
        return f"{v.month}/{v.day}/{v.year}"  # same order Google shows for this sheet
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def from_xlsx():
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(get(
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx")), data_only=True, read_only=True)
    out = {}
    for tab in TABS:
        if tab not in wb.sheetnames:
            continue
        raw = list(wb[tab].iter_rows(values_only=True))
        cols = [str(h or "").strip().lower() for h in (raw[0] if raw else [])]
        rows = [[cell(v, cols[i] if i < len(cols) else "") for i, v in enumerate(r)] for r in raw]
        while rows and not any(rows[-1]):
            rows.pop()
        buf = io.StringIO()
        csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n").writerows(rows)
        out[tab] = buf.getvalue()
    return out


def from_gviz(tab):
    text = get(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&headers=1&sheet="
               + urllib.parse.quote(tab)).decode("utf-8")
    if text.lstrip().startswith("<") or "google.visualization" in text[:200]:
        raise RuntimeError("sheet is not shared for viewing")
    return text


def main():
    os.makedirs(OUT, exist_ok=True)
    try:
        texts, via = from_xlsx(), "excel export"
    except Exception as e:
        print(f"excel export failed ({e}); using quick CSV link")
        texts, via = {}, "quick csv"
    for tab in TABS:
        if tab not in texts:
            try:
                texts[tab] = from_gviz(tab)
            except Exception as e:
                if tab in OPTIONAL:
                    continue
                sys.exit(f"Could not read '{tab}': {e}")
    changed = False
    for tab, looks_right in TABS.items():
        text = texts.get(tab)
        if text is None:
            continue
        head = ",".join(next(csv.reader(io.StringIO(text)), [])).lower()
        if not looks_right(head):
            if tab in OPTIONAL:
                print(f"skip {tab}: unexpected columns")
                continue
            sys.exit(f"'{tab}' has unexpected columns: {head[:200]}")
        path = os.path.join(OUT, f"{tab}.csv")
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old != text:
            open(path, "w", encoding="utf-8").write(text)
            changed = True
            print(f"updated {tab} ({text.count(chr(10))} lines, via {via})")
    if changed or not os.path.exists(os.path.join(OUT, "meta.json")):
        json.dump({"copiedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "via": via},
                  open(os.path.join(OUT, "meta.json"), "w"))
    print("changed" if changed else "no change")


if __name__ == "__main__":
    main()

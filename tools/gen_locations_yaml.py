from __future__ import annotations
from pathlib import Path
import csv
import re
import sys

try:
    from pykakasi import kakasi
except Exception:
    print("Missing dependency: pykakasi. Install with: pip3 install pykakasi", file=sys.stderr)
    raise


# Ignore non-location meta rows
IGNORE_EXACT = {
    "拠点", "城", "町", "忍の里", "海賊の砦",
    "目標拠点", "発生拠点", "主人公拠点", "主人公当主拠点",
    "主人公居城", "主人公当主居城",
    "拠点Ａ", "拠点Ｂ", "拠点Ｃ", "拠点Ｄ", "拠点Ｅ",
    "城Ａ", "城Ｂ", "城Ｃ", "城Ｄ", "城Ｅ",
    "町Ａ", "町Ｂ", "町Ｃ", "町Ｄ", "町Ｅ",
    "里Ａ", "里Ｂ", "里Ｃ", "里Ｄ", "里Ｅ",
    "砦Ａ", "砦Ｂ", "砦Ｃ", "砦Ｄ", "砦Ｅ",
    "無効",
}

PAT_CASTLE = re.compile(r".+城$")
PAT_TOWN   = re.compile(r".+の町$")
PAT_VILL   = re.compile(r".+の里$")
PAT_FORT   = re.compile(r".+砦$")


def is_real_location(jp: str) -> bool:
    if not jp or jp in IGNORE_EXACT:
        return False
    return bool(
        PAT_CASTLE.match(jp)
        or PAT_TOWN.match(jp)
        or PAT_VILL.match(jp)
        or PAT_FORT.match(jp)
    )


def strip_suffix(jp: str) -> tuple[str, str]:
    if PAT_CASTLE.match(jp):
        return "Castle", jp[:-1]
    if PAT_TOWN.match(jp):
        return "Town", jp[:-2]
    if PAT_VILL.match(jp):
        return "Village", jp[:-2]
    if PAT_FORT.match(jp):
        return "PirateBase", jp[:-1]
    raise ValueError(f"Unexpected location format: {jp}")


def build_kakasi():
    k = kakasi()
    k.setMode("H", "a")
    k.setMode("K", "a")
    k.setMode("J", "a")
    k.setMode("r", "Hepburn")
    k.setMode("s", True)
    return k.getConverter()


def pascalize(romaji: str) -> str:
    s = romaji.strip()
    s = re.sub(r"[^A-Za-z0-9\s\-']", " ", s)
    parts = re.split(r"[\s\-']+", s)
    parts = [p for p in parts if p]
    return "".join(p[:1].upper() + p[1:].lower() for p in parts)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 tools/gen_locations_yaml.py data/jp_tc_locations.csv enums/core/locations.yaml")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(2)

    conv = build_kakasi()

    rows: list[tuple[str, str]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header or len(header) < 2:
            print("CSV must have 2 columns: jp, tc", file=sys.stderr)
            sys.exit(3)

        for r in reader:
            if len(r) < 2:
                continue
            jp = (r[0] or "").strip()
            tc = (r[1] or "").strip()
            if not jp or not tc:
                continue
            if not is_real_location(jp):
                continue
            rows.append((jp, tc))

    out: dict[str, dict] = {}
    used_keys = set()

    for jp, tc in rows:
        kind, base = strip_suffix(jp)

        romaji_base = conv.do(base)
        key = kind + pascalize(romaji_base)

        # Avoid generic entries
        if base in {"城", "町", "里", "砦"}:
            continue

        if key in used_keys:
            n = 2
            while f"{key}{n}" in used_keys:
                n += 1
            key = f"{key}{n}"

        used_keys.add(key)

        out[key] = {
            "value": {
                "tc": tc,
                "sc": "",
                "jp": jp
            },
            "comment": "Generated from JP↔TC table"
        }

    # -------- Beautified output --------

    def group_order(k: str):
        if k.startswith("Castle"):
            return (0, k)
        if k.startswith("Town"):
            return (1, k)
        if k.startswith("Village"):
            return (2, k)
        if k.startswith("PirateBase"):
            return (3, k)
        return (9, k)

    keys_sorted = sorted(out.keys(), key=group_order)

    lines = []
    lines.append("# Auto-generated file. DO NOT EDIT.")
    lines.append("# Source: data/jp_tc_locations.csv")
    lines.append("")

    def emit_group(title: str, prefix: str):
        group_keys = [k for k in keys_sorted if k.startswith(prefix)]
        if not group_keys:
            return
        lines.append(f"# {title}")
        lines.append("")
        for k in group_keys:
            v = out[k]
            lines.append(f"{k}:")
            lines.append("  value:")
            lines.append(f"    tc: {v['value']['tc']}")
            lines.append(f"    sc: \"{v['value']['sc']}\"")
            lines.append(f"    jp: {v['value']['jp']}")
            lines.append(f"  comment: {v['comment']}")
            lines.append("")

    emit_group("Castles", "Castle")
    emit_group("Towns", "Town")
    emit_group("Ninja Villages", "Village")
    emit_group("Pirate Bases", "PirateBase")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"Generated: {out_path} ({len(out)} entries)")


if __name__ == "__main__":
    main()
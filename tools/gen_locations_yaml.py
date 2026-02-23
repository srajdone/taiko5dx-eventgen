from __future__ import annotations
from pathlib import Path
import csv
import re
import sys
import yaml

try:
    from pykakasi import kakasi
except Exception:
    print("Missing dependency: pykakasi. Install with: pip3 install pykakasi", file=sys.stderr)
    raise

# Rows to ignore (placeholders / meta)
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

# We only generate real location enums that match one of these:
# - ...城
# - ...の町
# - ...の里
# - ...砦
PAT_CASTLE = re.compile(r".+城$")
PAT_TOWN   = re.compile(r".+の町$")
PAT_VILL   = re.compile(r".+の里$")
PAT_FORT   = re.compile(r".+砦$")

def is_real_location(jp: str) -> bool:
    if not jp or jp in IGNORE_EXACT:
        return False
    return bool(PAT_CASTLE.match(jp) or PAT_TOWN.match(jp) or PAT_VILL.match(jp) or PAT_FORT.match(jp))

def strip_suffix(jp: str) -> tuple[str, str]:
    """Return (kind_prefix, base_name) where kind_prefix in {Castle,Town,Village,PirateBase}"""
    if PAT_CASTLE.match(jp):
        return "Castle", jp[:-1]  # remove "城"
    if PAT_TOWN.match(jp):
        return "Town", jp[:-2]    # remove "の町"
    if PAT_VILL.match(jp):
        return "Village", jp[:-2] # remove "の里"
    if PAT_FORT.match(jp):
        return "PirateBase", jp[:-1] # remove "砦"
    raise ValueError(f"Unexpected location format: {jp}")

def build_kakasi():
    k = kakasi()
    k.setMode("H", "a")
    k.setMode("K", "a")
    k.setMode("J", "a")
    # Hepburn-ish
    k.setMode("r", "Hepburn")
    k.setMode("s", True)   # add spaces
    k.setMode("C", True)   # capitalize (we still post-process)
    return k.getConverter()

def pascalize(romaji: str) -> str:
    # romaji may contain spaces/hyphens/apostrophes
    s = romaji.strip()
    s = re.sub(r"[^A-Za-z0-9\s\-']", " ", s)
    parts = re.split(r"[\s\-']+", s)
    parts = [p for p in parts if p]
    return "".join(p[:1].upper() + p[1:].lower() for p in parts)

def load_overrides(path: Path) -> dict[str, str]:
    """
    Optional overrides file for better keys:
    - key: jp_base (without suffix)
    - value: RomajiBase (PascalCase or raw; we pascalize anyway)

    Example:
      京: Kyoto
      大坂: Osaka
      江戸: Edo
      清洲: Kiyosu
      伊賀: Iga
      甲賀: Koga
      釜山: Busan
      寧波: Ningbo
      那覇: Naha
      呂宋: Luzon
    """
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("overrides.yaml must be a mapping")
    return {str(k): str(v) for k, v in data.items()}

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 tools/gen_locations_yaml.py data/jp_tc_locations.csv enums/core/locations.yaml [data/romaji_overrides.yaml]")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    overrides_path = Path(sys.argv[3]) if len(sys.argv) >= 4 else None

    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(2)

    overrides = load_overrides(overrides_path) if overrides_path else {}

    conv = build_kakasi()

    # read csv (two columns: jp, tc)
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

    # Build YAML mapping
    out = {}
    used_keys = set()

    for jp, tc in rows:
        kind, base = strip_suffix(jp)

        # romaji base: overrides first, else kakasi
        if base in overrides:
            romaji_base = overrides[base]
        else:
            romaji_base = conv.do(base)  # e.g. "gassan toda"
        key = kind + pascalize(romaji_base)

        # Avoid collisions: append number if needed
        if key in used_keys:
            n = 2
            while f"{key}{n}" in used_keys:
                n += 1
            key = f"{key}{n}"
        used_keys.add(key)

        out[key] = {
            "value": {"tc": tc, "sc": "", "jp": jp},
            "comment": "Generated from JP↔TC table",
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=True), encoding="utf-8")
    print(f"Generated: {out_path} ({len(out)} entries)")

if __name__ == "__main__":
    main()

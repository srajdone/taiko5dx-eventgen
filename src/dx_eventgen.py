import sys
import yaml
from pathlib import Path
import difflib

TAB = "\t"

def indent(level: int) -> str:
    return TAB * level

def dx_line(level: int, text: str) -> str:
    return indent(level) + text + "\n"

def load_map(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing enum map file: {path.as_posix()}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Enum map must be a YAML mapping (key:value): {path.as_posix()}")
    return data

def suggest_key(key: str, candidates: list[str]) -> str:
    matches = difflib.get_close_matches(key, candidates, n=3, cutoff=0.6)
    if matches:
        return " Did you mean: " + ", ".join(matches)
    return ""

class EnumMaps:
    def __init__(self, repo_root: Path):
        enums_dir = repo_root / "enums"
        self.towns = load_map(enums_dir / "towns.yaml")
        self.facilities = load_map(enums_dir / "facilities.yaml")
        self.characters = load_map(enums_dir / "characters.yaml")

    def town(self, key: str) -> str:
        if key in self.towns:
            return self.towns[key]
        raise KeyError(f"Unknown town '{key}'." + suggest_key(key, list(self.towns.keys())))

    def facility(self, key: str) -> str:
        if key in self.facilities:
            return self.facilities[key]
        raise KeyError(f"Unknown facility '{key}'." + suggest_key(key, list(self.facilities.keys())))

    def character(self, key: str) -> str:
        if key in self.characters:
            return self.characters[key]
        raise KeyError(f"Unknown character '{key}'." + suggest_key(key, list(self.characters.keys())))

def generate_event(data: dict, maps: EnumMaps) -> str:
    event_name = data["event_name"]
    once = data.get("once", True)

    trigger = data["trigger"]
    town_key = trigger["town"]
    facility_key = trigger["facility"]

    town = maps.town(town_key)
    facility = maps.facility(facility_key)

    script = data.get("script", [])

    output = ""
    output += "太閣立志傳５事件原始碼\n"
    output += "章節:{\n"
    output += dx_line(1, f"事件:{event_name}" + "{")

    if once:
        output += dx_line(2, "屬性:僅限一次")

    output += dx_line(2, f"發生時機:室內畫面顯示後({town},{facility})")
    output += dx_line(2, "發生條件:{")
    output += dx_line(2, "}")
    output += dx_line(2, "腳本:{")

    for cmd in script:
        if "narration" in cmd:
            output += dx_line(3, f"旁白:[[${cmd['narration']}]]".replace("$", ""))
        elif "hero_think" in cmd:
            output += dx_line(3, f"自言自語:[[${cmd['hero_think']}]]".replace("$", ""))
        elif "say" in cmd:
            sp_key = cmd["say"]["speaker"]
            ls_key = cmd["say"]["listener"]
            tx = cmd["say"]["text"]
            sp = maps.character(sp_key)
            ls = maps.character(ls_key)
            output += dx_line(3, f"對話:({sp},{ls})[[{tx}]]")
        elif "rename_say" in cmd:
            rs = cmd["rename_say"]
            sp = maps.character(rs["speaker"])
            ls = maps.character(rs["listener"])
            surname = rs["surname"]
            name = rs["name"]
            tx = rs["text"]
            output += dx_line(3, f"變名對話:({sp},{ls},[[{surname}]],[[{name}]])[[{tx}]]")
        else:
            raise ValueError(f"Unknown script command: {cmd}")

    output += dx_line(2, "}")
    output += dx_line(1, "}")
    output += "}\n"
    return output

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 src/dx_eventgen.py input.yaml output.txt")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    # Repo root = parent of src/
    repo_root = Path(__file__).resolve().parents[1]
    maps = EnumMaps(repo_root)

    data = yaml.safe_load(input_path.read_text(encoding="utf-8"))
    dx_script = generate_event(data, maps)

    # Write UTF-16 LE BOM
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dx_script, encoding="utf-16")

    print(f"Generated: {output_path}")

if __name__ == "__main__":
    main()

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
        return " Did you mean: " + ", ".join(matches) + " ?"
    return ""

class CompileError(Exception):
    def __init__(self, message: str, input_file: str = "", path: str = ""):
        parts = []
        if input_file:
            parts.append(f"File: {input_file}")
        if path:
            parts.append(f"Path: {path}")
        if parts:
            super().__init__("\n".join(parts) + "\nError: " + message)
        else:
            super().__init__(message)

class EnumMaps:
    def __init__(self, repo_root: Path):
        enums_dir = repo_root / "enums"
        self.towns = load_map(enums_dir / "towns.yaml")
        self.facilities = load_map(enums_dir / "facilities.yaml")
        self.characters = load_map(enums_dir / "characters.yaml")

    def map_town(self, key: str, *, input_file: str, path: str) -> str:
        if key in self.towns:
            return self.towns[key]
        raise CompileError(
            f"Unknown town '{key}'." + suggest_key(key, list(self.towns.keys())),
            input_file=input_file,
            path=path,
        )

    def map_facility(self, key: str, *, input_file: str, path: str) -> str:
        if key in self.facilities:
            return self.facilities[key]
        raise CompileError(
            f"Unknown facility '{key}'." + suggest_key(key, list(self.facilities.keys())),
            input_file=input_file,
            path=path,
        )

    def map_character(self, key: str, *, input_file: str, path: str) -> str:
        if key in self.characters:
            return self.characters[key]
        raise CompileError(
            f"Unknown character '{key}'." + suggest_key(key, list(self.characters.keys())),
            input_file=input_file,
            path=path,
        )

def generate_event(data: dict, maps: EnumMaps, *, input_file: str) -> str:
    # Basic structure validation (friendly errors)
    if not isinstance(data, dict):
        raise CompileError("Root YAML must be a mapping/object.", input_file=input_file, path="$")

    if "event_name" not in data:
        raise CompileError("Missing required field 'event_name'.", input_file=input_file, path="event_name")
    if "trigger" not in data:
        raise CompileError("Missing required field 'trigger'.", input_file=input_file, path="trigger")

    event_name = data["event_name"]
    once = bool(data.get("once", True))

    trigger = data["trigger"]
    if not isinstance(trigger, dict):
        raise CompileError("'trigger' must be an object.", input_file=input_file, path="trigger")

    for k in ("town", "facility"):
        if k not in trigger:
            raise CompileError(f"Missing required field 'trigger.{k}'.", input_file=input_file, path=f"trigger.{k}")

    town_key = trigger["town"]
    facility_key = trigger["facility"]

    town = maps.map_town(str(town_key), input_file=input_file, path="trigger.town")
    facility = maps.map_facility(str(facility_key), input_file=input_file, path="trigger.facility")

    script = data.get("script", [])
    if not isinstance(script, list):
        raise CompileError("'script' must be a list.", input_file=input_file, path="script")

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

    for i, cmd in enumerate(script):
        if not isinstance(cmd, dict):
            raise CompileError(
                f"Each script entry must be an object. Got: {type(cmd).__name__}",
                input_file=input_file,
                path=f"script[{i}]",
            )

        if "narration" in cmd:
            text = str(cmd["narration"])
            output += dx_line(3, f"旁白:[[${text}]]".replace("$", ""))

        elif "hero_think" in cmd:
            text = str(cmd["hero_think"])
            output += dx_line(3, f"自言自語:[[${text}]]".replace("$", ""))

        elif "say" in cmd:
            say = cmd["say"]
            if not isinstance(say, dict):
                raise CompileError("'say' must be an object.", input_file=input_file, path=f"script[{i}].say")
            for k in ("speaker", "listener", "text"):
                if k not in say:
                    raise CompileError(f"Missing '{k}' in say.", input_file=input_file, path=f"script[{i}].say.{k}")

            sp_key = str(say["speaker"])
            ls_key = str(say["listener"])
            tx = str(say["text"])

            sp = maps.map_character(sp_key, input_file=input_file, path=f"script[{i}].say.speaker")
            ls = maps.map_character(ls_key, input_file=input_file, path=f"script[{i}].say.listener")

            output += dx_line(3, f"對話:({sp},{ls})[[{tx}]]")

        elif "rename_say" in cmd:
            rs = cmd["rename_say"]
            if not isinstance(rs, dict):
                raise CompileError("'rename_say' must be an object.", input_file=input_file, path=f"script[{i}].rename_say")
            for k in ("speaker", "listener", "surname", "name", "text"):
                if k not in rs:
                    raise CompileError(f"Missing '{k}' in rename_say.", input_file=input_file, path=f"script[{i}].rename_say.{k}")

            sp_key = str(rs["speaker"])
            ls_key = str(rs["listener"])
            surname = str(rs["surname"])
            name = str(rs["name"])
            tx = str(rs["text"])

            sp = maps.map_character(sp_key, input_file=input_file, path=f"script[{i}].rename_say.speaker")
            ls = maps.map_character(ls_key, input_file=input_file, path=f"script[{i}].rename_say.listener")

            output += dx_line(3, f"變名對話:({sp},{ls},[[{surname}]],[[{name}]])[[{tx}]]")

        else:
            known = ["narration", "hero_think", "say", "rename_say"]
            raise CompileError(
                "Unknown script command. Expected one of: " + ", ".join(known),
                input_file=input_file,
                path=f"script[{i}]",
            )

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
    input_file = input_path.as_posix()

    try:
        # Repo root = parent of src/
        repo_root = Path(__file__).resolve().parents[1]
        maps = EnumMaps(repo_root)

        data = yaml.safe_load(input_path.read_text(encoding="utf-8"))
        dx_script = generate_event(data, maps, input_file=input_file)

        # Only write output AFTER everything succeeds
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(dx_script, encoding="utf-16")
        print(f"Generated: {output_path}")

    except CompileError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        # Unexpected error: still fail safely, no partial output
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(3)

if __name__ == "__main__":
    main()

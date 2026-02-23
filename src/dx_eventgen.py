import sys
import yaml
from pathlib import Path
import difflib

TAB = "\t"
DEFAULT_LANG = "tc"  # for now we only output Traditional Chinese (tc)

def dx_line(level: int, text: str) -> str:
    return (TAB * level) + text + "\n"

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

def load_enum_map(path: Path, lang: str = DEFAULT_LANG) -> dict:
    """
    Supported enum entry formats:

    Legacy (string):
      Hero: 主角

    New (object with multi-lang value):
      Hero:
        value:
          tc: 主角
          sc: ""
          jp: ""
        comment: Player character

    Rules:
      - If value.<lang> exists and is non-empty, use it.
      - Else fallback to value.tc if non-empty.
      - Else error.
    """
    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Enum file must be a YAML mapping: {path.as_posix()}")

    out = {}
    for k, v in data.items():
        k = str(k)

        # legacy: Key: "中文值"
        if isinstance(v, str):
            # Legacy only makes sense for tc output
            if lang != "tc":
                raise ValueError(
                    f"Legacy enum entry only supports tc output: {path.as_posix()} key '{k}'"
                )
            out[k] = v
            continue

        # new: Key: { value: { tc: "...", sc:"", jp:"" }, comment: "..." }
        if isinstance(v, dict) and "value" in v and isinstance(v["value"], dict):
            vv = v["value"]

            # preferred language
            if lang in vv and isinstance(vv[lang], str) and vv[lang].strip() != "":
                out[k] = vv[lang]
                continue

            # fallback to tc
            if "tc" in vv and isinstance(vv["tc"], str) and vv["tc"].strip() != "":
                out[k] = vv["tc"]
                continue

            raise ValueError(
                f"Enum entry missing value.{lang} (and no tc fallback): {path.as_posix()} key '{k}'"
            )

        raise ValueError(
            f"Invalid enum entry in {path.as_posix()} for key '{k}'. "
            f"Expected string OR object with value.tc"
        )

    return out

class EnumMaps:
    def __init__(self, repo_root: Path, lang: str = DEFAULT_LANG):
        self.lang = lang

        # Prefer enums/core/*.yaml; fallback to old enums/*.yaml
        core = repo_root / "enums" / "core"
        old = repo_root / "enums"

        # Helper: try core then old
        def load_core_then_old(filename: str) -> dict:
            m = load_enum_map(core / filename, lang=self.lang)
            if m:
                return m
            return load_enum_map(old / filename, lang=self.lang)

        self.towns = load_core_then_old("towns.yaml")
        self.facilities = load_core_then_old("facilities.yaml")
        self.characters = load_core_then_old("characters.yaml")
        self.gender = load_core_then_old("gender.yaml")
        self.faction_types = load_core_then_old("faction_types.yaml")

    def _map(self, mapping: dict, kind: str, key: str, *, input_file: str, path: str) -> str:
        key = str(key)
        if key in mapping:
            return mapping[key]
        raise CompileError(
            f"Unknown {kind} '{key}'." + suggest_key(key, list(mapping.keys())),
            input_file=input_file,
            path=path,
        )

    def town(self, key: str, *, input_file: str, path: str) -> str:
        return self._map(self.towns, "town", key, input_file=input_file, path=path)

    def facility(self, key: str, *, input_file: str, path: str) -> str:
        return self._map(self.facilities, "facility", key, input_file=input_file, path=path)

    def character(self, key: str, *, input_file: str, path: str) -> str:
        return self._map(self.characters, "character", key, input_file=input_file, path=path)

    def gender_value(self, key: str, *, input_file: str, path: str) -> str:
        return self._map(self.gender, "gender", key, input_file=input_file, path=path)

    def faction_type_value(self, key: str, *, input_file: str, path: str) -> str:
        return self._map(self.faction_types, "faction_type", key, input_file=input_file, path=path)

def emit_time_before_year_month(level: int, year: int, month: int) -> str:
    # before (Y,M): year<Y OR (year==Y AND month<M)
    out = ""
    out += dx_line(level, "ＯＲ調查:{")
    out += dx_line(level + 1, f"調查:(狀況::年)<({year})")
    out += dx_line(level + 1, "ＡＮＤ調查:{")
    out += dx_line(level + 2, f"調查:(狀況::年)==({year})")
    out += dx_line(level + 2, f"調查:(狀況::月)<({month})")
    out += dx_line(level + 1, "}")
    out += dx_line(level, "}")
    return out

def compile_require(require: dict, maps: EnumMaps, *, input_file: str) -> str:
    """
    Supported require keys:
      - gender: Male/Female
      - no_task: true
      - faction_type: NinjaClan/Ronin/Daimyo
      - money_gt: int
      - before_year_month: {year:int, month:int}
    """
    if require is None:
        return ""
    if not isinstance(require, dict):
        raise CompileError("'require' must be an object.", input_file=input_file, path="require")

    out = ""

    if "before_year_month" in require:
        bym = require["before_year_month"]
        if not isinstance(bym, dict):
            raise CompileError("'before_year_month' must be an object.", input_file=input_file, path="require.before_year_month")
        if "year" not in bym or "month" not in bym:
            raise CompileError("before_year_month requires 'year' and 'month'.", input_file=input_file, path="require.before_year_month")
        year = int(bym["year"])
        month = int(bym["month"])
        out += emit_time_before_year_month(3, year, month)

    if "gender" in require:
        g = maps.gender_value(require["gender"], input_file=input_file, path="require.gender")
        out += dx_line(3, f"調查:(人物::主角.性別)==({g})")

    if require.get("no_task", False):
        out += dx_line(3, "調查:(人物::主角.主命狀態)==(無主命)")

    if "faction_type" in require:
        ft = maps.faction_type_value(require["faction_type"], input_file=input_file, path="require.faction_type")
        out += dx_line(3, f"調查:(人物::主角.所屬勢力類型)==({ft})")

    if "money_gt" in require:
        mg = int(require["money_gt"])
        out += dx_line(3, f"調查:(主角.持有金)>({mg})")

    return out

def compile_script_block(script: list, maps: EnumMaps, *, input_file: str, base_path: str, level: int) -> str:
    if not isinstance(script, list):
        raise CompileError("Script block must be a list.", input_file=input_file, path=base_path)

    out = ""
    for i, cmd in enumerate(script):
        p = f"{base_path}[{i}]"
        if not isinstance(cmd, dict):
            raise CompileError("Each script entry must be an object.", input_file=input_file, path=p)

        if "narration" in cmd:
            text = str(cmd["narration"])
            out += dx_line(level, f"旁白:[[${text}]]".replace("$", ""))

        elif "hero_think" in cmd:
            text = str(cmd["hero_think"])
            out += dx_line(level, f"自言自語:[[${text}]]".replace("$", ""))

        elif "say" in cmd:
            say = cmd["say"]
            if not isinstance(say, dict):
                raise CompileError("'say' must be an object.", input_file=input_file, path=f"{p}.say")
            for k in ("speaker", "listener", "text"):
                if k not in say:
                    raise CompileError(f"Missing '{k}' in say.", input_file=input_file, path=f"{p}.say.{k}")

            sp = maps.character(say["speaker"], input_file=input_file, path=f"{p}.say.speaker")
            ls = maps.character(say["listener"], input_file=input_file, path=f"{p}.say.listener")
            tx = str(say["text"])
            out += dx_line(level, f"對話:({sp},{ls})[[{tx}]]")

        elif "rename_say" in cmd:
            rs = cmd["rename_say"]
            if not isinstance(rs, dict):
                raise CompileError("'rename_say' must be an object.", input_file=input_file, path=f"{p}.rename_say")
            for k in ("speaker", "listener", "surname", "name", "text"):
                if k not in rs:
                    raise CompileError(f"Missing '{k}' in rename_say.", input_file=input_file, path=f"{p}.rename_say.{k}")

            sp = maps.character(rs["speaker"], input_file=input_file, path=f"{p}.rename_say.speaker")
            ls = maps.character(rs["listener"], input_file=input_file, path=f"{p}.rename_say.listener")
            surname = str(rs["surname"])
            name = str(rs["name"])
            tx = str(rs["text"])
            out += dx_line(level, f"變名對話:({sp},{ls},[[{surname}]],[[{name}]])[[{tx}]]")

        elif "choice" in cmd:
            choice = cmd["choice"]
            if not isinstance(choice, dict):
                raise CompileError("'choice' must be an object.", input_file=input_file, path=f"{p}.choice")
            if "options" not in choice or not isinstance(choice["options"], list):
                raise CompileError("choice.options must be a list.", input_file=input_file, path=f"{p}.choice.options")

            options = choice["options"]
            labels = []
            for oi, opt in enumerate(options):
                op = f"{p}.choice.options[{oi}]"
                if not isinstance(opt, dict):
                    raise CompileError("Each option must be an object.", input_file=input_file, path=op)
                if "label" not in opt:
                    raise CompileError("Missing option.label", input_file=input_file, path=f"{op}.label")
                if "do" not in opt:
                    raise CompileError("Missing option.do", input_file=input_file, path=f"{op}.do")
                labels.append(str(opt["label"]))

            out += dx_line(level, "選擇:(" + "".join([f"[[{lb}]]" for lb in labels]) + ")")

            for oi, opt in enumerate(options):
                op = f"{p}.choice.options[{oi}]"
                lb = str(opt["label"])
                out += dx_line(level, f"分歧:([[{lb}]])" + "{")
                out += compile_script_block(opt["do"], maps, input_file=input_file, base_path=f"{op}.do", level=level + 1)
                out += dx_line(level, "}")

        else:
            known = ["narration", "hero_think", "say", "rename_say", "choice"]
            raise CompileError(
                "Unknown script command. Expected one of: " + ", ".join(known),
                input_file=input_file,
                path=p,
            )

    return out

def generate_event(data: dict, maps: EnumMaps, *, input_file: str) -> str:
    if not isinstance(data, dict):
        raise CompileError("Root YAML must be an object.", input_file=input_file, path="$")

    if "event_name" not in data:
        raise CompileError("Missing required field 'event_name'.", input_file=input_file, path="event_name")
    if "trigger" not in data:
        raise CompileError("Missing required field 'trigger'.", input_file=input_file, path="trigger")

    trigger = data["trigger"]
    if not isinstance(trigger, dict):
        raise CompileError("'trigger' must be an object.", input_file=input_file, path="trigger")
    if "town" not in trigger or "facility" not in trigger:
        raise CompileError("trigger requires 'town' and 'facility'.", input_file=input_file, path="trigger")

    event_name = str(data["event_name"])
    once = bool(data.get("once", True))

    town = maps.town(trigger["town"], input_file=input_file, path="trigger.town")
    facility = maps.facility(trigger["facility"], input_file=input_file, path="trigger.facility")

    require_block = compile_require(data.get("require", None), maps, input_file=input_file)

    script = data.get("script", [])
    script_block = compile_script_block(script, maps, input_file=input_file, base_path="script", level=3)

    out = ""
    out += "太閣立志傳５事件原始碼\n"
    out += "章節:{\n"
    out += dx_line(1, f"事件:{event_name}" + "{")
    if once:
        out += dx_line(2, "屬性:僅限一次")
    out += dx_line(2, f"發生時機:室內畫面顯示後({town},{facility})")
    out += dx_line(2, "發生條件:{")
    out += require_block
    out += dx_line(2, "}")
    out += dx_line(2, "腳本:{")
    out += script_block
    out += dx_line(2, "}")
    out += dx_line(1, "}")
    out += "}\n"
    return out

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 src/dx_eventgen.py input.yaml output.txt")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    input_file = input_path.as_posix()

    try:
        repo_root = Path(__file__).resolve().parents[1]
        maps = EnumMaps(repo_root, lang=DEFAULT_LANG)

        data = yaml.safe_load(input_path.read_text(encoding="utf-8"))
        dx_script = generate_event(data, maps, input_file=input_file)

        # Only write output after success
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(dx_script, encoding="utf-16")

        print(f"Generated: {output_path}")

    except CompileError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(3)

if __name__ == "__main__":
    main()

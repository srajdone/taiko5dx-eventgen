import sys
import yaml
from pathlib import Path
import difflib

TAB = "\t"
DEFAULT_LANG = "tc"  # current output target

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
    Supports:
      Legacy: Key: "DXValue"
      New:
        Key:
          value:
            tc: ...
            sc: ""
            jp: ""
          comment: ...
    Returns: dict[key] = resolved_value_string
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

        if isinstance(v, str):
            if lang != "tc":
                raise ValueError(f"Legacy enum entry only supports tc: {path.as_posix()} key '{k}'")
            out[k] = v
            continue

        if isinstance(v, dict) and "value" in v and isinstance(v["value"], dict):
            vv = v["value"]

            if lang in vv and isinstance(vv[lang], str) and vv[lang].strip() != "":
                out[k] = vv[lang].strip()
                continue

            if "tc" in vv and isinstance(vv["tc"], str) and vv["tc"].strip() != "":
                out[k] = vv["tc"].strip()
                continue

            raise ValueError(f"Enum entry missing value.{lang} (and no tc fallback): {path.as_posix()} key '{k}'")

        raise ValueError(
            f"Invalid enum entry in {path.as_posix()} for key '{k}'. "
            f"Expected string OR object with value.tc"
        )

    return out

class EnumRegistry:
    """
    Auto-load all enums/core/*.yaml as categories by filename stem.
      enums/core/characters.yaml -> category 'characters'
      enums/core/locations.yaml  -> category 'locations'
      enums/core/bgm.yaml        -> category 'bgm'
      enums/core/sfx.yaml        -> category 'sfx'
    """
    def __init__(self, repo_root: Path, lang: str = DEFAULT_LANG):
        self.lang = lang
        self.categories: dict[str, dict[str, str]] = {}

        core_dir = repo_root / "enums" / "core"
        old_dir = repo_root / "enums"  # legacy fallback (optional)

        if core_dir.exists():
            for p in sorted(core_dir.glob("*.yaml")):
                cat = p.stem
                self.categories[cat] = load_enum_map(p, lang=self.lang)

        # legacy fallback only if core missing that category
        if old_dir.exists():
            for p in sorted(old_dir.glob("*.yaml")):
                cat = p.stem
                if cat not in self.categories or not self.categories[cat]:
                    m = load_enum_map(p, lang=self.lang)
                    if m:
                        self.categories[cat] = m

    def get(self, category: str, key: str, *, input_file: str, path: str) -> str:
        category = str(category)
        key = str(key)
        if category not in self.categories:
            raise CompileError(
                f"Unknown enum category '{category}'. Available: {', '.join(sorted(self.categories.keys()))}",
                input_file=input_file,
                path=path,
            )
        mapping = self.categories[category]
        if key in mapping:
            return mapping[key]
        raise CompileError(
            f"Unknown {category} '{key}'." + suggest_key(key, list(mapping.keys())),
            input_file=input_file,
            path=path,
        )

def emit_time_before_year_month(level: int, year: int, month: int) -> str:
    out = ""
    out += dx_line(level, "ＯＲ調查:{")
    out += dx_line(level + 1, f"調查:(狀況::年)<({year})")
    out += dx_line(level + 1, "ＡＮＤ調查:{")
    out += dx_line(level + 2, f"調查:(狀況::年)==({year})")
    out += dx_line(level + 2, f"調查:(狀況::月)<({month})")
    out += dx_line(level + 1, "}")
    out += dx_line(level, "}")
    return out

def compile_require(require: dict, enums: EnumRegistry, *, input_file: str) -> str:
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
        out += emit_time_before_year_month(3, int(bym["year"]), int(bym["month"]))

    if "gender" in require:
        g = enums.get("gender", require["gender"], input_file=input_file, path="require.gender")
        out += dx_line(3, f"調查:(人物::主角.性別)==({g})")

    if require.get("no_task", False):
        out += dx_line(3, "調查:(人物::主角.主命狀態)==(無主命)")

    if "faction_type" in require:
        ft = enums.get("faction_types", require["faction_type"], input_file=input_file, path="require.faction_type")
        out += dx_line(3, f"調查:(人物::主角.所屬勢力類型)==({ft})")

    if "money_gt" in require:
        out += dx_line(3, f"調查:(主角.持有金)>({int(require['money_gt'])})")

    return out

def compile_script_block(script: list, enums: EnumRegistry, *, input_file: str, base_path: str, level: int) -> str:
    if not isinstance(script, list):
        raise CompileError("Script block must be a list.", input_file=input_file, path=base_path)

    out = ""
    for i, cmd in enumerate(script):
        p = f"{base_path}[{i}]"
        if not isinstance(cmd, dict):
            raise CompileError("Each script entry must be an object.", input_file=input_file, path=p)

        if "narration" in cmd:
            out += dx_line(level, f"旁白:[[${str(cmd['narration'])}]]".replace("$", ""))

        elif "hero_think" in cmd:
            out += dx_line(level, f"自言自語:[[${str(cmd['hero_think'])}]]".replace("$", ""))

        elif "bgm" in cmd:
            bgm_val = enums.get("bgm", cmd["bgm"], input_file=input_file, path=f"{p}.bgm")
            out += dx_line(level, f"背景音樂變更:({bgm_val})")

        elif "sfx" in cmd:
            sfx_val = enums.get("sfx", cmd["sfx"], input_file=input_file, path=f"{p}.sfx")
            out += dx_line(level, f"音效開始:({sfx_val})")

        elif "say" in cmd:
            say = cmd["say"]
            if not isinstance(say, dict):
                raise CompileError("'say' must be an object.", input_file=input_file, path=f"{p}.say")
            for k in ("speaker", "listener", "text"):
                if k not in say:
                    raise CompileError(f"Missing '{k}' in say.", input_file=input_file, path=f"{p}.say.{k}")

            sp = enums.get("characters", say["speaker"], input_file=input_file, path=f"{p}.say.speaker")
            ls = enums.get("characters", say["listener"], input_file=input_file, path=f"{p}.say.listener")
            out += dx_line(level, f"對話:({sp},{ls})[[{str(say['text'])}]]")

        elif "rename_say" in cmd:
            rs = cmd["rename_say"]
            if not isinstance(rs, dict):
                raise CompileError("'rename_say' must be an object.", input_file=input_file, path=f"{p}.rename_say")
            for k in ("speaker", "listener", "surname", "name", "text"):
                if k not in rs:
                    raise CompileError(f"Missing '{k}' in rename_say.", input_file=input_file, path=f"{p}.rename_say.{k}")

            sp = enums.get("characters", rs["speaker"], input_file=input_file, path=f"{p}.rename_say.speaker")
            ls = enums.get("characters", rs["listener"], input_file=input_file, path=f"{p}.rename_say.listener")
            out += dx_line(level, f"變名對話:({sp},{ls},[[{rs['surname']}]],[[{rs['name']}]])[[{rs['text']}]]")

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
                out += compile_script_block(opt["do"], enums, input_file=input_file, base_path=f"{op}.do", level=level + 1)
                out += dx_line(level, "}")

        else:
            known = ["narration", "hero_think", "bgm", "sfx", "say", "rename_say", "choice"]
            raise CompileError(
                "Unknown script command. Expected one of: " + ", ".join(known),
                input_file=input_file,
                path=p,
            )

    return out

def generate_event(data: dict, enums: EnumRegistry, *, input_file: str) -> str:
    if not isinstance(data, dict):
        raise CompileError("Root YAML must be an object.", input_file=input_file, path="$")

    if "event_name" not in data:
        raise CompileError("Missing required field 'event_name'.", input_file=input_file, path="event_name")
    if "trigger" not in data:
        raise CompileError("Missing required field 'trigger'.", input_file=input_file, path="trigger")

    trigger = data["trigger"]
    if not isinstance(trigger, dict):
        raise CompileError("'trigger' must be an object.", input_file=input_file, path="trigger")

    # NEW: trigger.location (preferred). OLD: trigger.town (compat)
    if "location" in trigger:
        loc_key = trigger["location"]
        loc_path = "trigger.location"
    elif "town" in trigger:
        loc_key = trigger["town"]
        loc_path = "trigger.town"
    else:
        raise CompileError("trigger requires 'location' (preferred) or 'town' (legacy).", input_file=input_file, path="trigger.location")

    if "facility" not in trigger:
        raise CompileError("trigger requires 'facility'.", input_file=input_file, path="trigger.facility")

    event_name = str(data["event_name"])
    once = bool(data.get("once", True))

    location = enums.get("locations", loc_key, input_file=input_file, path=loc_path)
    facility = enums.get("facilities", trigger["facility"], input_file=input_file, path="trigger.facility")

    require_block = compile_require(data.get("require", None), enums, input_file=input_file)
    script_block = compile_script_block(data.get("script", []), enums, input_file=input_file, base_path="script", level=3)

    out = ""
    out += "太閣立志傳５事件原始碼\n"
    out += "章節:{\n"
    out += dx_line(1, f"事件:{event_name}" + "{")
    if once:
        out += dx_line(2, "屬性:僅限一次")
    out += dx_line(2, f"發生時機:室內畫面顯示後({location},{facility})")
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
        enums = EnumRegistry(repo_root, lang=DEFAULT_LANG)

        data = yaml.safe_load(input_path.read_text(encoding="utf-8"))
        dx_script = generate_event(data, enums, input_file=input_file)

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

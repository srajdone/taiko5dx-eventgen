import sys import yaml from pathlib import Path

TAB = “

def indent(level): return TAB * level

def dx_line(level, text): return indent(level) + text + “”

def generate_event(data): event_name = data[“event_name”] once =
data.get(“once”, True)

    trigger = data["trigger"]
    town = trigger["town"]
    facility = trigger["facility"]

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
            sp = cmd["say"]["speaker"]
            ls = cmd["say"]["listener"]
            tx = cmd["say"]["text"]
            output += dx_line(3, f"對話:({sp},{ls})[[{tx}]]")
        elif "rename_say" in cmd:
            rs = cmd["rename_say"]
            output += dx_line(
                3,
                f"變名對話:({rs['speaker']},{rs['listener']},[[{rs['surname']}]],[[{rs['name']}]])[[{rs['text']}]]"
            )

    output += dx_line(2, "}")
    output += dx_line(1, "}")
    output += "}\n"

    return output

def main(): if len(sys.argv) != 3: print(“Usage: python dx_eventgen.py
input.yaml output.txt”) sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    with open(input_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    dx_script = generate_event(data)

    # Write UTF-16 LE BOM (required by DX editor)
    with open(output_path, "w", encoding="utf-16") as f:
        f.write(dx_script)

    print(f"Generated: {output_path}")

if name == “main”: main()

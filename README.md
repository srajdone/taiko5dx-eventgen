# Taiko5DX EventGen

Write Taiko Risshiden 5 DX events in YAML and compile them into valid DX
event scripts automatically.

------------------------------------------------------------------------

Why?

Writing Taiko 5 DX event scripts directly is painful:

-   CJK-based syntax
-   Strict formatting rules (Tab only)
-   Crashes on invalid enum values
-   Manual variable assignment required
-   UTF-16 LE BOM encoding requirement
-   Hard to maintain large event projects

This project provides a modern YAML-based front-end that compiles into
valid DX script files.

You write clean YAML. The compiler generates valid DX script.

------------------------------------------------------------------------

Goals

-   Human-friendly event authoring
-   Automatic DX syntax generation
-   Automatic UTF-16 LE BOM output
-   Enum validation (no more editor crashes)
-   Safe money assignment expansion
-   Community-driven event scripting standard

------------------------------------------------------------------------

Current Status

Early development (v0.1)

Currently supported:

-   Facility trigger
-   Once-only events
-   Dialogue
-   Rename dialogue
-   Narration
-   Basic choice branching
-   Add money (safe assignment expansion)

------------------------------------------------------------------------

Example (YAML)

event_name: Kiyosu_RiceShop_MysteryWoman once: true

trigger: type: enter_facility town: 清洲之町 facility: 米屋

script: - narration: “A strange laughter is heard from behind the
counter.” - rename_say: speaker: 喝醉的女人 listener: 主角 surname: 神秘
name: 女子 text: “Looking for the shop owner?”

------------------------------------------------------------------------

Roadmap

-   ☐ Enum validation system
-   ☐ Time condition helpers
-   ☐ Advanced branching
-   ☐ Auto extraction from official DX documentation
-   ☐ Community template library
-   ☐ CLI tool support
-   ☐ Mac / Windows script support

------------------------------------------------------------------------

Vision

The long-term goal is to provide a modern scripting layer for Taiko 5
DX, allowing the community to create large-scale, modular, maintainable
event projects without touching the original DX syntax.

------------------------------------------------------------------------

License

MIT

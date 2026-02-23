# Taiko5DX EventGen

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![Status](https://img.shields.io/badge/status-early--development-orange)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Mac%20%7C%20Windows-lightgrey)

Write Taiko Risshiden 5 DX events in YAML and compile them into valid DX event scripts automatically.

## Why?

Writing Taiko 5 DX event scripts directly is painful:

- CJK-based syntax
- Strict formatting rules (Tab only)
- Crashes on invalid enum values
- Manual variable assignment required
- UTF-16 LE BOM encoding requirement
- Hard to maintain large event projects

This project provides a modern YAML-based front-end that compiles into valid DX script files.

You write clean YAML. The compiler generates valid DX script.

## Goals

- Human-friendly event authoring
- Automatic DX syntax generation
- Automatic UTF-16 LE BOM output
- Enum validation (no more editor crashes)
- Safe condition expansion
- Community-driven event scripting standard

## Current Status

Early development (v0.2)

Currently supported:

- Facility trigger
- Once-only events
- Dialogue
- Rename dialogue
- Narration
- Choice branching
- Condition DSL (gender, faction, money, time)
- Strict enum validation

## Example (YAML)

```yaml
event_name: Kiyosu_RiceShop_MysteryWoman
once: true

trigger:
  town: KiyosuTown
  facility: RiceShop

script:
  - narration: "A strange laughter is heard from behind the counter."
  - rename_say:
      speaker: DrunkenWoman
      listener: Hero
      surname: Mysterious
      name: Woman
      text: "Looking for the shop owner?"
```

# Enum System

This project separates:

DSL Layer (English keys)  
→ Language Resolver  
→ DX Script Output  

You NEVER write raw DX enum strings in YAML scripts.

Instead:

```
Hero → 主角
RiceShop → 米屋
NinjaClan → 忍者眾
```

All mappings are defined in:

```
enums/core/
```

## Enum Structure

Each enum entry must follow this format:

```yaml
SomeKey:
  value:
    tc: 繁體中文值
    sc: 简体中文值
    jp: 日本語漢字
  comment: Optional explanation
```

### Language Order

1. tc — Traditional Chinese (currently used)
2. sc — Simplified Chinese (reserved)
3. jp — Japanese (reserved)

Even if sc and jp are not used yet:

- They must remain in the structure.
- Leave them as empty string if unknown.

### Correct Example

```yaml
Temple:
  value:
    tc: 寺
    sc: ""
    jp: ""
  comment: Temple facility
```

### Incorrect Example

```yaml
Temple:
  value:
    tc: 寺
```

## Adding New Enums

1. Choose the correct file inside:

```
enums/core/
```

Examples:

- towns.yaml
- facilities.yaml
- characters.yaml
- gender.yaml
- faction_types.yaml

2. Add a new entry using PascalCase key:

```yaml
RiceMerchant:
  value:
    tc: 米商
    sc: ""
    jp: ""
  comment: Rice merchant NPC
```

### Naming Rules

- Use English PascalCase
- No spaces
- No Chinese in keys
- Avoid ambiguity
- Prefer explicit names (e.g., NinjaClan instead of Ninja)

## Validation

The compiler will:

- Reject unknown enum keys
- Suggest similar names
- Stop safely without generating output file

Example:

```
File: examples/test.yaml
Path: script[2].say.speaker
Error: Unknown character 'Herro'. Did you mean: Hero ?
```

## Roadmap

- ☐ Multi-language output support (tc / sc / jp)
- ☐ Advanced condition helpers
- ☐ Nested branching improvements
- ☐ Official DX documentation parser
- ☐ Community template library
- ☐ CLI packaging
- ☐ Visual editor prototype

## Vision

The long-term goal is to provide a modern scripting layer for Taiko Risshiden 5 DX, allowing the community to create large-scale, modular, maintainable event projects without touching the original DX syntax.

This project aims to become the standard DSL layer for Taiko DX event development.

## License

MIT

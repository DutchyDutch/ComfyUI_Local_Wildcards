# ComfyUI Local Wildcards
![Version](https://img.shields.io/badge/version-v1.2.0-blue.svg)

A robust localized wildcard, random choices, and nested pattern expansion node for ComfyUI.
Supports simple `.txt` files, hierarchical structured `.yaml` / `.yml` configurations, and nested `.json` formats. It is designed as a powerful, lightweight replacement for older wildcard nodes that are no longer maintained.

## Features

- **`__wildcard__` syntax** — pulls a random line/value from a matching wildcard file (e.g. `__color__`, `__folder/color__`)
- **Dynamic prompt syntax** — inline random choices without needing a file, e.g. `{red|blue|green}`
- **Weighted choices** — bias certain options to appear more/less often, e.g. `{red::0.2|blue::0.8}`
- **Multi-select** — pick several options at once, e.g. `{2$$red|blue|green}` or a random range `{1-3$$red|blue|green}`
- **Custom separators** — control how multiple picks are joined, e.g. `{1-3$$ and $$red|blue|green}`
- **Wildcards inside dynamic prompts** — combine both systems, e.g. `{1-3$$ and $$__Round__}`
- **Nested wildcards** — wildcard results can themselves contain more `__wildcards__` or `{dynamic|prompts}`, fully resolved recursively
- **Glob pattern matching** — reference a random file within a folder, e.g. `__folder/*__`
- **Escape characters** — use `\{`, `\}`, `\|`, `\$`, `\_` to include these characters literally
- **Multiple file formats** — `.txt`, `.yaml`/`.yml`, and `.json` wildcard files are all supported
- **Seed control** — `seed_mode` (`fixed`/`random`) and `seed` inputs let you lock in a specific combination or randomize every run
- **Insert Wildcard dropdown** — browse all detected wildcards, grouped by folder, and insert them into your prompt without typing
- **Live preview box** — after running, see the fully resolved text with resolved parts highlighted in 【 】 brackets, while the plain output text (sent to your generation nodes) stays clean
- **Auto-refresh** — wildcard files are automatically rescanned when changed; no restart needed

## Quick Start

### 1. Installation

**Option A — Via ComfyUI Manager (recommended)**
Search for `ComfyUI Local Wildcards` in the Manager's custom node browser and click Install.

**Option B — Manual Install**
Open your terminal inside your ComfyUI `custom_nodes` folder and run:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/DutchyDutch/ComfyUI_Local_Wildcards.git

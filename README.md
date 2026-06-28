\# ComfyUI Local Wildcards



A robust localized wildcard, random choices, and nested pattern expansion node for ComfyUI. 

Supports text `.txt`, hierarchical structured `.yaml` / `.yml` configurations, and nested `.json` formats.



\## Features



\- \*\*Format Agnostic\*\*: Seamlessly parses `.txt` files (simple lists), structured nested `.json`, and block folded `.yaml` structures (with native support for standard line folds `>` and `>-`).

\- \*\*Path-Based Display Names\*\*: Dropdown items retain directory trees to make searching highly intuitive (e.g., `\_\_BoChars/male/modern\_\_`).

\- \*\*Dynamic Random Option Selectors\*\*: Supports inline brackets syntax inside files or prompts like:

&#x20; - `{Option A | Option B | Option C}`

&#x20; - `{|| empty or chance of blush}` (supports zero-value weighted probabilities)

\- \*\*Nested Wildcard Resolutions\*\*: Resolves wildcards that call deeper paths or other dynamic wildcards recursively up to 30 directories deep!

\- \*\*Dynamic Glob Patterns\*\*: Selects randomly from matches using asterisk syntax like `\_\_hairstyles\_\*\_\_`.



\## Installation



Run this directly inside your standard ComfyUI custom nodes terminal:



```bash

cd ComfyUI/custom\_nodes

git clone https://github.com/DutchyDutch/ComfyUI\_Local\_Wildcards.git


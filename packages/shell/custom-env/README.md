---
description: "Sets Host env defaults and $DSH_HOME/.env for model shell children."
kind: "package-reference"
---

# @deepseek-ai/dsh-custom-env

At load, merges a package-local default map with `$DSH_HOME/.env` (file wins on conflict) and assigns the result onto the Host `process.env` so bash/pwsh children inherit those keys. On Windows it also writes the same keys into the current user's environment. A missing or empty `.env` leaves only the defaults.

## Model Experience

Shell and skill scripts can read the merged keys (for example `$VERTAX_COMFYUI_ENDPOINT`). No model-visible prompt text is added.

## Known Limitations and Deferred Work

- Values are fixed when the plugin loads; restart the Host after editing `$DSH_HOME/.env` or the default map.
- Windows user env updates apply to new processes; already-open terminals keep their old block.
- Non-Windows hosts only set the current process environment.
- Names matching the subprocess credential scrub (`*KEY*`, `*SECRET*`, `*TOKEN*`, `*PASSWORD*`) may not reach shell children unless re-injected after scrub.
- No `./invariant` export: the plugin only assigns process and user environment values.

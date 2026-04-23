# TODO

## sync.sh
- Check if sync is starting HDD when nothing to sync
- Create a script to kill a process created by sync.sh

## reboot_router.sh
- Move hardcoded router IP and password to `.env` (follow `sync.sh` pattern); add entry to `.env.example`
- Replace fragile `cut -c"25-45"` CSRF token extraction with a regex — breaks on any firmware HTML change
- Add `set -euo pipefail`

## brightness.sh
- Fix broken line 7 (incomplete / missing closing quote and arg) — script likely does not run as-is
- Validate input argument before passing to `xrandr`

## server-backup.sh
- Add retention policy — tar.gz archives currently accumulate in `/var/backup` forever
- Add `set -euo pipefail` and quote variables

## publish-mvn-server-and-npm-client.sh
- Placeholder paths were never filled in — either complete the script or delete it

## setup-mint-desktop.sh
- Empty stub (21 bytes) — implement or remove

## temp-monitoring.sh
- Add `set -euo pipefail`
- Add logging so reboot events are traceable

## Repo-wide
- `.gitignore`: add `__pycache__/`, `*.pyc`, `.env`, `*.swp`, `.DS_Store`
- Standardize shebangs on `#!/usr/bin/env bash` across all scripts
- Add `set -euo pipefail` to any remaining Bash scripts missing it
- Expand `README.md` with a one-line-per-script index and prerequisites
- Run `shellcheck` over `utils/ system/ cron/` and fix warnings

## media-renamer

### P1 — High Impact
- Load `config.json` in `main()` with a user-facing error message instead of at module import time (currently crashes on import if missing/malformed)
- Fix TOCTOU race condition in collision handling (`media_renamer.py:136`) — use `Path.replace()` or catch `FileExistsError` instead of pre-checking existence
- Check `ffprobe` exit code (`media_renamer.py:240`) — currently a failed ffprobe silently returns no data, leading to wrong timestamps

### P2 — Medium Impact
- Log skipped (unknown-type) files at DEBUG level with reason (`media_renamer.py:100`) — currently silent
- Fix naive datetimes for video `creation_time` (`media_renamer.py:254`) — parse `Z` suffix as UTC with `timezone.utc` or `datetime.fromisoformat()`
- Case-insensitive device code matching (`media_renamer.py:200`) — EXIF model strings may not match config keys exactly

### P3 — Polish
- Add `--verbose` / `--quiet` CLI flag — log level is hardcoded to INFO
- Add progress reporting for large folders (counter every N files or `tqdm`)
- Add `frozen=True` to `Metadata` dataclass to prevent accidental mutation
- Replace hardcoded `year == 1970` epoch check with a configurable threshold (`media_renamer.py:172`)

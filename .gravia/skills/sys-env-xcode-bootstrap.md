---
name: sys-env-xcode-bootstrap
description: System-level bootstrap protocol to verify Xcode Command Line Tools on Apple Silicon.
---

# sys-env-xcode-bootstrap

This skill ensures that the macOS environment is correctly anchored to the developer toolchain before initiating build or simulation tasks.

## MANDATORY PRE-FLIGHT CHECK
Before running any `gravia` commands that rely on `git`, `make`, or C-compilers, the agent MUST verify the toolchain:

```bash
xcode-select -p
```

## ERROR HANDLING
If the command fails or returns an error regarding `/var/db/xcode_select_link`, the agent MUST NOT attempt to bypass the error. Instead, it must trigger the following **BETA-THETA Purge Protocol**:

1. **Purge**: `sudo rm -rf /Library/Developer/CommandLineTools`
2. **Reset**: `sudo xcode-select --reset`
3. **Reinstall**: `xcode-select --install`

## EXIT CRITERIA
The environment is considered stable ONLY if `xcode-select -p` returns a valid path (e.g., `/Library/Developer/CommandLineTools` or `/Applications/Xcode.app/Contents/Developer`).

# CHANGELOG

> History of kiro-iso-builder — newest first.

---

## 2026-06-07 — Initial GTK4 app

First working version of the Kiro ISO Builder: a GTK4 (ATT-style, plain Gtk4 — no
libadwaita) front-end that drives `kiro-iso/build-scripts/build-the-iso.sh` rather than
reimplementing it.

### What Changed

- **Four-screen wizard** (StackSidebar + Stack, ATT look): Pre-flight → Configure → Build → Done.
- **Pre-flight panel** — 11 host checks with one-click fixes that reuse `host-prep.sh`
  (`ensure_package`, `setup_chaotic`, `setup_cachyos`) so a GUI-fixed host equals a
  CLI-prepared one. Checks: repo present, not-root, Arch-based, polkit agent, `archiso`,
  `grub`, Chaotic, CachyOS, disk space, kernel tokens, NVIDIA choice.
- **Configure screen** — reads/writes the shared `build.conf` (`nvidia_driver`, `kernel`,
  `bump_version`, plus advanced knobs). No sed-editing of the build script. The kernel is
  chosen via two dropdowns — **First kernel** (boots the live ISO) and an optional **Second
  kernel** (`none` collapses to a single-kernel build). A **Detect available kernels** button
  loads the real list from the host via the shared `list-kernels.sh` (same filter the build
  uses — only kernels that have a matching `-headers`, no false positives), falling back to a
  curated list. Headers are not a separate choice: the build installs `<kernel>-headers`
  automatically for every selected kernel (required for the DKMS drivers).
- **Packages screen** (new wizard step between Configure and Build) — lists the ISO's
  **TIER 3** (user-changeable / optional) packages from `packages.x86_64`, grouped by category,
  reusing ATT's "streamline" pattern: category-level select-all (tri-state), per-package
  checkboxes, and a search filter. Unticked packages are written to `package-selection.conf`,
  which the build comments out — TIER 1/2 are never shown, so nothing here can break the build.
  **Save profile / Import profile** (also from streamline) export the current exclusion set to a
  file and load it back, so the same package set can be reused for a later rebuild. Profiles live
  in `~/.config/kiro-iso-builder/profiles/`, created at startup (ATT-style `ensure_app_dirs()`).
- **Persistent Quit button** in the window's bottom-right footer, on every screen.
- **Reset to defaults** button on the Configure screen — restores every knob to its shipped
  default (review, then Save to persist; shares one code path with the normal load).
- **Build progress** maps `Phase N` log lines to the bar; the total is auto-derived from the
  build script (12 phases today) so it never shows "Phase 11 / 9" again.
- **Build screen** — runs the build under a **PTY** so its internal `sudo` gets a tty and
  prompts once (answered via a GTK password dialog), then streams a live log and maps
  `Phase N` lines to a progress bar. Stoppable. An **input box** lets the user answer any
  prompt the build raises (e.g. mkarchiso/pacman's `[Y/n]`) by writing to the PTY master, and
  log output is **ANSI-stripped** so terminal colour codes don't clutter the view. The PTY is
  given a real window size (`TIOCSWINSZ`) and in-place progress bars (carriage-return redraws)
  collapse to their final state, so a big package no longer floods the log with hundreds of
  identical lines.
- **Done screen** — open `~/kiro-Out`, show checksums, and test-boot the ISO in **QEMU or
  VirtualBox**. Both create a throwaway **UEFI** VM (OVMF / `--firmware efi`, not legacy BIOS)
  with a **50 GB disk** so the Calamares installer has a target, and both **overwrite** a single
  reusable test VM/disk (`kiro-iso-builder-test`) — fresh every run, no clutter. When a
  hypervisor is missing the button becomes **Install QEMU** / **Install VirtualBox** (pkexec) and
  flips back to Test once installed; the VirtualBox install (adapted from Erik's script) pulls
  `virtualbox` + `virtualbox-host-dkms`, the `-headers` for every installed kernel, loads and
  persists the modules, and adds the user to `vboxusers`.

### Technical Details

- **Privilege model:** app runs as the normal user (never root). Fixes elevate via
  `pkexec bash host-prep-run.sh <fn>`; the build runs as the user and authenticates its own
  `sudo` inside the PTY. Wayland-safe — no root-owned GUI ever touches the display.
- **Portable:** no hardcoded paths/users; repo discovery via `KIRO_ISO_DIR`, sibling clone,
  `~/kiro-iso`, or `/usr/share`; Arch detection via `os-release` `ID`/`ID_LIKE`.
- **Pairs with kiro-iso changes:** the build config block was extracted into
  `build-scripts/build.conf`, and a thin `host-prep-run.sh` dispatcher was added so the GUI
  can invoke a single host-prep function in isolation.

### Files

- `kiro-iso-builder.py` (entry/Application/Window), `functions.py` (runners + config bridge),
  `host_checks.py`, `preflight_gui.py`, `configure_gui.py`, `build_gui.py`, `done_gui.py`,
  `style.css`, `kiro-iso-builder.desktop`, `README.md`.

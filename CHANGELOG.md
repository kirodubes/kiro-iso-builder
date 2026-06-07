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
- **Build robustness fixes** — the PTY runner now exports `TERM=xterm-256color` so the build's
  `tput` calls don't abort with "No value for $TERM" when the app is launched from a desktop
  menu (where `TERM` is unset). The kernel pre-flight check now distinguishes "kiro-iso repo not
  yet present", `kernel=ask` (chosen at build time), and "no kernel set in build.conf" (a real
  WARN) instead of collapsing them all to a single misleading message.
- **Done screen** — open `~/kiro-Out`, show checksums, and test-boot the ISO in **QEMU or
  VirtualBox**. Both create a throwaway **UEFI** VM (OVMF / `--firmware efi`, not legacy BIOS)
  with a **50 GB disk** so the Calamares installer has a target. Boot order is **disk-first, CD
  fallback** (QEMU `-boot order=cd`, VirtualBox `--boot1 disk --boot2 dvd`) so an empty disk boots
  the ISO installer but the post-install reboot boots the installed system instead of looping the
  ISO. Both **overwrite** a single reusable test VM/disk (`kiro-iso-builder-test`) — fresh every
  run, no clutter. When a
  hypervisor is missing the button becomes **Install QEMU** / **Install VirtualBox** (pkexec) and
  flips back to Test once installed; the VirtualBox install (adapted from Erik's script) pulls
  `virtualbox` + `virtualbox-host-dkms`, the `-headers` for every installed kernel, loads and
  persists the modules, and adds the user to `vboxusers`.
- **Stale-mount fail-safe** — stopping a build halfway used to leave mkarchiso's bind-mounts
  (`dev/proc/sys/run/tmp/pts/shm/efivars`) live under the work dir, which blocks the next build,
  jams the file manager, and can freeze the host (it did — hard reboot). Now: (1) the **Build
  screen** runs a cleanup after any abnormal exit (Stop **or** failure) — it first checks for
  leftover mounts as the user (no prompt) and only `pkexec`-unmounts if some remain, re-arming
  **Start** only once clean; (2) a new **Pre-flight check** ("Stale build mounts") surfaces
  leftovers from an earlier crash with a one-click Fix; (3) `build-the-iso.sh` now unmounts on
  any early exit via an `EXIT` trap (the net — also covers a `set -e` build failure), with
  `INT`/`TERM` traps on top so a `Ctrl-C`/`kill` (CLI or the GUI's Stop) cleans up immediately.
  Backed by
  a new self-contained `kiro-iso/build-scripts/unmount-build.sh` (`check` = read-only detect,
  `clean` = unmount) that derives the work dir the same way the build does — one source of truth
  shared by the Stop handler, the pre-flight check, and the CLI.
- **build.conf is now a gitignored working copy** — the kiro-iso repo ships a tracked
  `build.conf.defaults` and gitignores the live `build.conf`. `ensure_build_conf()` seeds it from
  the defaults at app startup and after a clone (`refresh_paths`), so the GUI always has a real
  config to read/write while the user's local build tweaks can never be committed/pushed back to
  the repo.
- **Shareable build profiles** — a build can now be saved as a named, shareable
  `*.kiroprofile` that captures the **ISO-identity settings** (`desktop`, `kernel`,
  `nvidia_driver`) **plus** the removed-package set, so someone else can reproduce the
  same ISO recipe. **Save build profile…** lives on the Done screen (after a build),
  **Import build profile…** on the Configure screen (it populates the settings controls
  and writes `package-selection.conf`, so the Packages screen reflects it — then Save &
  Continue). Host/workflow knobs (`build_location`, `clean_pacman_cache`,
  `remove_build_folder`, `bump_version`) are deliberately **not** captured — they're
  about the builder's machine, not the ISO. The file records the recipe, not a
  byte-identical image (Kiro is rolling). The pre-existing package-only Save/Import
  buttons were relabelled **Save/Import package list…** to distinguish them.
- **Choose where the kiro-iso repo lives** — the Pre-flight screen now shows a
  **kiro-iso location** row with a **Browse…** button, so the user can point the app at
  an existing clone anywhere or pick where a new one should be cloned (instead of the old
  hardcoded `~/kiro-iso`). The choice is persisted to `~/.config/kiro-iso-builder/repo_path`
  and tried first by repo discovery, so it survives a relaunch; the clone fix targets it
  (and persists a freshly-cloned default too). Browsing to a folder that already holds the
  repo uses it as-is; otherwise the repo is created as `<folder>/kiro-iso`. Distinct from
  the `build_location` knob (which only moves `kiro-build`/`kiro-Out`).

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
- Stale-mount fail-safe: `functions.py` (`unmount_build_script`, `stale_mounts_present`,
  `run_cleanup_mounts`), `build_gui.py` (cleanup-on-abnormal-exit), `host_checks.py`
  (`check_stale_mounts`), `preflight_gui.py` (`unmount` fix). Pairs with new
  `kiro-iso/build-scripts/unmount-build.sh` + `INT`/`TERM` trap in `build-the-iso.sh`.
- build.conf seeding: `functions.py` (`build_conf_defaults_path`, `ensure_build_conf`,
  seed in `refresh_paths`), `kiro-iso-builder.py` (seed at startup). Pairs with
  `kiro-iso`'s gitignored `build.conf` + tracked `build.conf.defaults`.
- Build profiles: `functions.py` (`write_build_profile`/`read_build_profile`,
  `PROFILE_SETTINGS_KEYS`), `done_gui.py` (Save), `configure_gui.py` (Import),
  `packages_gui.py` (relabel).
- Repo-location chooser: `functions.py` (`default_repo_dir`, `saved_repo_path`,
  `save_repo_path`, `resolve_repo_dir`, discovery order), `host_checks.py`
  (`clone_cmd(dest)`), `preflight_gui.py` (Browse row + clone-fix persistence).

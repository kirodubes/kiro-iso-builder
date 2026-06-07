"""Pre-flight screen — runs host checks and offers one-click fixes."""

import threading

import gi

import functions as fn
import host_checks as hc

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

_ICON = {hc.OK: "emblem-ok-symbolic",
         hc.WARN: "dialog-warning-symbolic",
         hc.FAIL: "dialog-error-symbolic"}


class PreflightScreen:
    def __init__(self, window):
        self.window = window
        self.rows = {}
        self._fix_queue = []

        self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.widget.set_margin_top(18)
        self.widget.set_margin_bottom(18)
        self.widget.set_margin_start(18)
        self.widget.set_margin_end(18)

        title = Gtk.Label(label="Pre-flight checks", xalign=0)
        title.add_css_class("screen-title")
        self.widget.append(title)
        subtitle = Gtk.Label(
            label="Confirm the host is ready, then fix anything red before building.",
            xalign=0)
        subtitle.add_css_class("dim-label")
        self.widget.append(subtitle)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.recheck_btn = Gtk.Button(label="Re-check")
        self.recheck_btn.connect("clicked", lambda _w: self.refresh())
        self.fixall_btn = Gtk.Button(label="Fix all")
        self.fixall_btn.add_css_class("suggested-action")
        self.fixall_btn.connect("clicked", lambda _w: self._fix_all())
        toolbar.append(self.recheck_btn)
        toolbar.append(self.fixall_btn)
        self.widget.append(toolbar)

        self.listbox = Gtk.ListBox()
        self.listbox.add_css_class("boxed-list")
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scroller = Gtk.ScrolledWindow(vexpand=True)
        scroller.set_child(self.listbox)
        self.widget.append(scroller)

        log_exp = Gtk.Expander(label="Fix log")
        self.log_view = Gtk.TextView(editable=False, monospace=True, cursor_visible=False)
        self.log_buf = self.log_view.get_buffer()
        log_scroll = Gtk.ScrolledWindow(min_content_height=140)
        log_scroll.set_child(self.log_view)
        log_exp.set_child(log_scroll)
        self.widget.append(log_exp)

        self.continue_btn = Gtk.Button(label="Continue to Configure →")
        self.continue_btn.add_css_class("suggested-action")
        self.continue_btn.set_halign(Gtk.Align.END)
        self.continue_btn.connect("clicked", lambda _w: self.window.navigate("configure"))
        self.widget.append(self.continue_btn)

    def on_show(self):
        if not self.rows:
            self.refresh()

    # ── checks ──────────────────────────────────────────────────────
    def refresh(self):
        self.recheck_btn.set_sensitive(False)
        self._log("Running checks…")

        def worker():
            results = hc.run_all()
            GLib.idle_add(self._populate, results)

        threading.Thread(target=worker, daemon=True).start()

    def _populate(self, results):
        child = self.listbox.get_first_child()
        while child:
            self.listbox.remove(child)
            child = self.listbox.get_first_child()
        self.rows.clear()
        for r in results:
            self.listbox.append(self._build_row(r))
        self.recheck_btn.set_sensitive(True)
        n_fail = sum(1 for r in results if r["status"] == hc.FAIL)
        self.continue_btn.set_sensitive(n_fail == 0)
        self.fixall_btn.set_sensitive(any(r["fix"] for r in results))

    def _build_row(self, r):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(10)
        box.set_margin_end(10)

        icon = Gtk.Image.new_from_icon_name(_ICON[r["status"]])
        icon.add_css_class(f"status-{r['status']}")
        box.append(icon)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        title = Gtk.Label(label=r["title"], xalign=0)
        title.add_css_class("row-title")
        detail = Gtk.Label(label=r["detail"], xalign=0, wrap=True)
        detail.add_css_class("dim-label")
        text.append(title)
        text.append(detail)
        box.append(text)

        if r["fix"]:
            btn = Gtk.Button(label="Fix")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", lambda _w, key=r["key"]: self._fix_one(key))
            box.append(btn)
            self.rows[r["key"]] = {"row": row, "fix": r["fix"], "btn": btn}

        row.set_child(box)
        return row

    # ── fixes ───────────────────────────────────────────────────────
    def _fix_all(self):
        self._fix_queue = list(self.rows.keys())
        self._next_in_queue()

    def _next_in_queue(self):
        if not self._fix_queue:
            self.refresh()
            return
        self._fix_one(self._fix_queue.pop(0), chained=True)

    def _fix_one(self, key, chained=False):
        entry = self.rows.get(key)
        if not entry:
            self._next_in_queue() if chained else None
            return
        entry["btn"].set_sensitive(False)
        kind = entry["fix"][0]
        self._log(f"── Fixing {key} ──")

        def done(code):
            self._log(f"[{'ok' if code == 0 else 'failed'}] {key} (exit {code})")
            if chained:
                self._next_in_queue()
            else:
                self.refresh()

        if kind == "hostprep":
            fn.run_hostprep_fix(entry["fix"][1], self._log, done)
        elif kind == "unmount":
            fn.run_cleanup_mounts(self._log, done)
        elif kind == "clone":
            cmd = hc.clone_cmd()
            if cmd is None:
                self._log("[error] git not installed — cannot clone kiro-iso")
                done(1)
                return
            fn.run_pipe(cmd, self._log, lambda c: (fn.refresh_paths(), done(c))[1])
        else:
            done(0)

    # ── log ─────────────────────────────────────────────────────────
    def _log(self, line):
        end = self.log_buf.get_end_iter()
        self.log_buf.insert(end, line + "\n")

"""Done screen — open the output, show checksums, offer a QEMU test boot."""

import subprocess
from pathlib import Path

import gi

import functions as fn

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402


def _out_folder():
    """Mirror build-the-iso.sh: home -> ~/kiro-Out, local -> beside the clone."""
    if fn.BUILD_SCRIPTS is None:
        return None
    if fn.read_conf().get("build_location") == "local":
        return fn.BUILD_SCRIPTS.parent.parent / "kiro-Out"
    return Path.home() / "kiro-Out"


def _latest_iso(folder):
    isos = sorted(folder.glob("*.iso"), key=lambda p: p.stat().st_mtime, reverse=True)
    return isos[0] if isos else None


class DoneScreen:
    def __init__(self, window):
        self.window = window
        self.iso = None

        self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for m in ("set_margin_top", "set_margin_bottom", "set_margin_start", "set_margin_end"):
            getattr(self.widget, m)(18)

        title = Gtk.Label(label="Build complete", xalign=0)
        title.add_css_class("screen-title")
        self.widget.append(title)

        self.info = Gtk.Label(xalign=0, wrap=True, selectable=True)
        self.widget.append(self.info)

        self.checks = Gtk.TextView(editable=False, monospace=True, cursor_visible=False)
        self.checks_buf = self.checks.get_buffer()
        scroller = Gtk.ScrolledWindow(min_content_height=140, vexpand=True)
        scroller.set_child(self.checks)
        self.widget.append(scroller)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.open_btn = Gtk.Button(label="Open output folder")
        self.open_btn.connect("clicked", lambda _w: self._open())
        self.vm_btn = Gtk.Button(label="Test in a VM")
        self.vm_btn.connect("clicked", lambda _w: self._test_vm())
        again = Gtk.Button(label="Build again")
        again.connect("clicked", lambda _w: self.window.navigate("preflight"))
        bar.append(self.open_btn)
        bar.append(self.vm_btn)
        bar.append(again)
        self.widget.append(bar)

    def on_show(self):
        folder = _out_folder()
        self.checks_buf.set_text("")
        if folder is None or not folder.is_dir():
            self.info.set_text("Output folder not found yet.")
            self._enable(False)
            return
        self.iso = _latest_iso(folder)
        if self.iso is None:
            self.info.set_text(f"No ISO found in {folder}")
            self._enable(False)
            return
        size_gb = self.iso.stat().st_size / 1_000_000_000
        self.info.set_text(f"{self.iso.name}\n{size_gb:.2f} GB  ·  {folder}")
        self._enable(True)
        for ext in ("sha256", "sha1", "md5"):
            f = self.iso.with_name(self.iso.name + "." + ext)
            if f.is_file():
                self.checks_buf.insert(self.checks_buf.get_end_iter(), f.read_text())

    def _enable(self, on):
        self.open_btn.set_sensitive(on)
        self.vm_btn.set_sensitive(on)

    def _open(self):
        folder = _out_folder()
        if folder:
            fn.open_path(folder)

    def _test_vm(self):
        if not self.iso:
            return
        if fn.have("qemu-system-x86_64"):
            subprocess.Popen([
                "qemu-system-x86_64", "-enable-kvm", "-m", "4096",
                "-boot", "d", "-cdrom", str(self.iso),
            ])
        else:
            self.checks_buf.insert(
                self.checks_buf.get_end_iter(),
                f"\nqemu not installed. Try:\n  qemu-system-x86_64 -enable-kvm -m 4096 "
                f"-boot d -cdrom {self.iso}\n")

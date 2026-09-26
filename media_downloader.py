#!/usr/bin/env python3
"""
MediaDownloader v3.8 — GTK4 / libadwaita
Mejoras:
 - Subtítulos (español + automáticos)
 - Incrustar miniatura y metadatos
 - SponsorBlock (eliminar anuncios/sponsors)
 - Cookies del navegador (Firefox / Chrome / Chromium)
 - Detección y reparación de binarios yt-dlp corruptos
 - Preferencia por "python3 -m yt_dlp"
 - Progreso porcentual, reintentos, cancelación limpia
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, Gio, Gdk

import threading
import subprocess
import shutil
import os
import json
import re
import collections
import sys
from pathlib import Path
from datetime import datetime

USER_BIN = Path.home() / ".local" / "bin"
USER_BIN.mkdir(parents=True, exist_ok=True)
os.environ["PATH"] = f"{USER_BIN}:/usr/local/bin:{os.environ.get('PATH', '')}"

CONFIG_DIR   = Path.home() / ".config" / "media-downloader"
CONFIG_FILE  = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"

LOG_FLUSH_MS  = 300
LOG_MAX_LINES = 800


def load_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {
        "download_path": str(Path.home() / "Downloads"),
        "notify": True,
        "theme": "system",
        "subs": False,
        "embed": True,
        "sponsorblock": False,
        "cookies": "none",
    }

def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def load_history():
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            pass
    return []

def save_history(h):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(h[-100:], indent=2))

def send_notification(title, body):
    try:
        subprocess.run(["notify-send", "-i", "folder-download", "-t", "4000", title, body], capture_output=True)
    except Exception:
        pass


def _is_working_ytdlp(cmd_list):
    try:
        r = subprocess.run(cmd_list + ["--version"], capture_output=True, text=True, timeout=15)
        return r.returncode == 0 and bool(r.stdout.strip())
    except Exception:
        return False


def get_ytdlp_cmd():
    for py in (sys.executable, "python3", "python"):
        if not py:
            continue
        candidate = [py, "-m", "yt_dlp"]
        if _is_working_ytdlp(candidate):
            return candidate

    which = shutil.which("yt-dlp")
    if which:
        if _is_working_ytdlp([which]):
            return [which]
        try:
            Path(which).unlink(missing_ok=True)
        except Exception:
            pass

    user_bin = USER_BIN / "yt-dlp"
    if user_bin.exists():
        if _is_working_ytdlp([str(user_bin)]):
            return [str(user_bin)]
        try:
            user_bin.unlink(missing_ok=True)
        except Exception:
            pass

    return None


def install_ytdlp(callback):
    def _run():
        methods = [
            [sys.executable, "-m", "pip", "install", "--quiet", "--user", "yt-dlp"],
            ["pip3", "install", "--quiet", "--user", "yt-dlp"],
            ["pip3", "install", "--quiet", "--break-system-packages", "yt-dlp"],
            ["pip",  "install", "--quiet", "yt-dlp"],
        ]
        for cmd in methods:
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=180)
                if r.returncode == 0 and get_ytdlp_cmd():
                    GLib.idle_add(callback, True, " ".join(cmd[:3]))
                    return
            except Exception:
                pass

        url  = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
        dest = USER_BIN / "yt-dlp"
        for dl in [["wget", "-qO", str(dest), url], ["curl", "-sSL", url, "-o", str(dest)]]:
            try:
                dest.unlink(missing_ok=True)
                r = subprocess.run(dl, capture_output=True, timeout=120)
                if r.returncode == 0 and dest.exists() and dest.stat().st_size > 10000:
                    dest.chmod(0o755)
                    if _is_working_ytdlp([str(dest)]):
                        GLib.idle_add(callback, True, f"descarga directa a {dest.name}")
                        return
                    dest.unlink(missing_ok=True)
            except Exception:
                pass
        GLib.idle_add(callback, False, "")
    threading.Thread(target=_run, daemon=True).start()


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="MediaDownloader")
        self.set_default_size(760, 820)
        self.set_resizable(True)
        self.set_icon_name("io.github.MediaDownloader")

        self.cfg         = load_config()
        self.history     = load_history()
        self.process     = None
        self.downloading = False
        self.ytdlp_ok    = False
        self._ytdlp_cmd  = None

        self._log_queue   = collections.deque()
        self._log_lock    = threading.Lock()
        self._flush_timer = None
        self._pulse_timer = None

        self._pl_total   = 0
        self._pl_done    = 0
        self._current_pl = False

        self._apply_theme(self.cfg.get("theme", "system"))
        self._build_ui()
        self._check_ytdlp()

    def _apply_theme(self, theme_str):
        sm = Adw.StyleManager.get_default()
        if theme_str == "dark":
            sm.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        elif theme_str == "light":
            sm.set_color_scheme(Adw.ColorScheme.PREFER_LIGHT)
        else:
            sm.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def _build_ui(self):
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        toolbar_view = Adw.ToolbarView()
        self.toast_overlay.set_child(toolbar_view)

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(
            title="MediaDownloader",
            subtitle="Descarga video y música de cualquier plataforma"))

        hist_btn = Gtk.Button(label="Historial")
        hist_btn.set_icon_name("document-open-recent-symbolic")
        hist_btn.add_css_class("flat")
        hist_btn.connect("clicked", self._show_history)
        header.pack_start(hist_btn)

        upd_btn = Gtk.Button(label="Actualizar yt-dlp")
        upd_btn.set_icon_name("software-update-available-symbolic")
        upd_btn.add_css_class("flat")
        upd_btn.connect("clicked", self._update_ytdlp)
        header.pack_end(upd_btn)

        toolbar_view.add_top_bar(header)

        scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        toolbar_view.set_content(scroll)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_margin_start(18)
        main_box.set_margin_end(18)
        scroll.set_child(main_box)

        # URL
        url_group = Adw.PreferencesGroup(title="URL")
        url_group.set_description("Pega el enlace del video, canción o lista")
        main_box.append(url_group)
        self.url_entry = Adw.EntryRow(title="https://…")
        self.url_entry.set_show_apply_button(False)
        url_group.add(self.url_entry)

        paste_btn = Gtk.Button(label="✂  Pegar desde portapapeles")
        paste_btn.add_css_class("pill")
        paste_btn.set_halign(Gtk.Align.START)
        paste_btn.connect("clicked", self._paste_url)
        main_box.append(paste_btn)

        # Tipo
        type_group = Adw.PreferencesGroup(title="Tipo de descarga")
        main_box.append(type_group)

        self.toggle_video = Gtk.ToggleButton(label="🎬  Video")
        self.toggle_audio = Gtk.ToggleButton(label="🎵  Solo Audio")
        self.toggle_audio.set_group(self.toggle_video)
        self.toggle_video.set_active(True)
        self.toggle_video.add_css_class("suggested-action")
        self.toggle_video.connect("toggled", self._on_mode_toggle)
        self.toggle_audio.connect("toggled", self._on_mode_toggle)

        toggle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toggle_box.set_homogeneous(True)
        toggle_box.append(self.toggle_video)
        toggle_box.append(self.toggle_audio)
        toggle_box.set_margin_bottom(4)
        type_group.add(toggle_box)

        pl_row = Adw.ActionRow(
            title="Descargar lista completa",
            subtitle="Descarga toda la playlist si la URL es una lista")
        self.pl_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        pl_row.add_suffix(self.pl_switch)
        pl_row.set_activatable_widget(self.pl_switch)
        type_group.add(pl_row)

        # Calidad
        opt_group = Adw.PreferencesGroup(title="Calidad y formato")
        main_box.append(opt_group)

        quality_row = Adw.ActionRow(title="Calidad")
        self.quality_combo = Gtk.DropDown.new_from_strings(
            ["Mejor disponible", "1080p", "720p", "480p", "360p"])
        self.quality_combo.set_valign(Gtk.Align.CENTER)
        quality_row.add_suffix(self.quality_combo)
        opt_group.add(quality_row)

        format_row = Adw.ActionRow(title="Formato")
        self.format_combo = Gtk.DropDown.new_from_strings(["MP4", "MKV", "WEBM"])
        self.format_combo.set_valign(Gtk.Align.CENTER)
        format_row.add_suffix(self.format_combo)
        opt_group.add(format_row)

        # Opciones avanzadas
        adv_group = Adw.PreferencesGroup(title="Opciones avanzadas")
        main_box.append(adv_group)

        subs_row = Adw.ActionRow(
            title="Descargar subtítulos",
            subtitle="Español + automáticos (si están disponibles)")
        self.subs_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.subs_switch.set_active(self.cfg.get("subs", False))
        self.subs_switch.connect("state-set", self._save_prefs)
        subs_row.add_suffix(self.subs_switch)
        subs_row.set_activatable_widget(self.subs_switch)
        adv_group.add(subs_row)

        embed_row = Adw.ActionRow(
            title="Incrustar miniatura y metadatos",
            subtitle="Guarda la carátula y la info dentro del archivo")
        self.embed_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.embed_switch.set_active(self.cfg.get("embed", True))
        self.embed_switch.connect("state-set", self._save_prefs)
        embed_row.add_suffix(self.embed_switch)
        embed_row.set_activatable_widget(self.embed_switch)
        adv_group.add(embed_row)

        sb_row = Adw.ActionRow(
            title="SponsorBlock (eliminar sponsors)",
            subtitle="Quita anuncios, intros y segmentos patrocinados")
        self.sb_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.sb_switch.set_active(self.cfg.get("sponsorblock", False))
        self.sb_switch.connect("state-set", self._save_prefs)
        sb_row.add_suffix(self.sb_switch)
        sb_row.set_activatable_widget(self.sb_switch)
        adv_group.add(sb_row)

        cookies_row = Adw.ActionRow(
            title="Cookies del navegador",
            subtitle="Útil para vídeos con restricción de edad o privados")
        self.cookies_combo = Gtk.DropDown.new_from_strings(
            ["Ninguno", "Firefox", "Chrome", "Chromium"])
        self.cookies_combo.set_valign(Gtk.Align.CENTER)
        cookies_map = {"none": 0, "firefox": 1, "chrome": 2, "chromium": 3}
        self.cookies_combo.set_selected(cookies_map.get(self.cfg.get("cookies", "none"), 0))
        self.cookies_combo.connect("notify::selected", self._on_cookies_changed)
        cookies_row.add_suffix(self.cookies_combo)
        adv_group.add(cookies_row)

        # Apariencia
        theme_group = Adw.PreferencesGroup(title="Apariencia y Preferencias")
        main_box.append(theme_group)

        theme_row = Adw.ActionRow(title="Tema de la interfaz")
        self.theme_combo = Gtk.DropDown.new_from_strings(["Sistema", "Oscuro", "Claro"])
        self.theme_combo.set_valign(Gtk.Align.CENTER)
        theme_map = {"system": 0, "dark": 1, "light": 2}
        self.theme_combo.set_selected(theme_map.get(self.cfg.get("theme", "system"), 0))
        self.theme_combo.connect("notify::selected", self._on_theme_changed)
        theme_row.add_suffix(self.theme_combo)
        theme_group.add(theme_row)

        notif_row = Adw.ActionRow(
            title="Notificaciones de escritorio",
            subtitle="Avisar al completar cada descarga")
        self.notif_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.notif_switch.set_active(self.cfg.get("notify", True))
        self.notif_switch.connect("state-set", self._save_prefs)
        notif_row.add_suffix(self.notif_switch)
        notif_row.set_activatable_widget(self.notif_switch)
        theme_group.add(notif_row)

        # Destino
        dest_group = Adw.PreferencesGroup(title="Destino")
        main_box.append(dest_group)
        self.dest_row = Adw.ActionRow(
            title="Carpeta de descarga",
            subtitle=GLib.markup_escape_text(
                self.cfg.get("download_path", str(Path.home() / "Downloads"))))
        folder_btn = Gtk.Button(icon_name="folder-open-symbolic", valign=Gtk.Align.CENTER)
        folder_btn.add_css_class("flat")
        folder_btn.connect("clicked", self._choose_dir)
        self.dest_row.add_suffix(folder_btn)
        dest_group.add(self.dest_row)

        # Progreso
        prog_group = Adw.PreferencesGroup(title="Progreso")
        main_box.append(prog_group)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_pulse_step(0.06)
        self.progress_bar.set_margin_start(8)
        self.progress_bar.set_margin_end(8)
        self.progress_bar.set_margin_top(4)
        prog_group.add(self.progress_bar)

        self.status_row = Adw.ActionRow(title="Listo para descargar")
        self.status_row.add_css_class("property")
        prog_group.add(self.status_row)

        log_frame = Gtk.Frame()
        log_frame.add_css_class("card")
        log_sw = Gtk.ScrolledWindow()
        log_sw.set_min_content_height(120)
        log_sw.set_max_content_height(140)
        log_sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.log_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView(
            buffer=self.log_buffer,
            editable=False, cursor_visible=False,
            monospace=True, wrap_mode=Gtk.WrapMode.WORD)
        self.log_view.set_margin_start(8)
        self.log_view.set_margin_end(8)
        self.log_view.set_margin_top(6)
        self.log_view.set_margin_bottom(6)
        log_sw.set_child(self.log_view)
        log_frame.set_child(log_sw)
        prog_group.add(log_frame)

        # Botones
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_box.set_halign(Gtk.Align.CENTER)
        action_box.set_margin_top(6)
        main_box.append(action_box)

        self.dl_btn = Gtk.Button(label="⬇  Descargar")
        self.dl_btn.add_css_class("suggested-action")
        self.dl_btn.add_css_class("pill")
        self.dl_btn.set_size_request(180, 44)
        self.dl_btn.connect("clicked", self._start_download)
        action_box.append(self.dl_btn)

        self.cancel_btn = Gtk.Button(label="✕  Cancelar")
        self.cancel_btn.add_css_class("destructive-action")
        self.cancel_btn.add_css_class("pill")
        self.cancel_btn.set_size_request(130, 44)
        self.cancel_btn.set_sensitive(False)
        self.cancel_btn.connect("clicked", self._cancel)
        action_box.append(self.cancel_btn)

    def _on_theme_changed(self, combo, _pspec):
        themes = ["system", "dark", "light"]
        selected = themes[combo.get_selected()]
        self.cfg["theme"] = selected
        save_config(self.cfg)
        self._apply_theme(selected)

    def _on_cookies_changed(self, combo, _pspec):
        values = ["none", "firefox", "chrome", "chromium"]
        self.cfg["cookies"] = values[combo.get_selected()]
        save_config(self.cfg)

    def _save_prefs(self, *_):
        self.cfg["notify"]       = self.notif_switch.get_active()
        self.cfg["subs"]         = self.subs_switch.get_active()
        self.cfg["embed"]        = self.embed_switch.get_active()
        self.cfg["sponsorblock"] = self.sb_switch.get_active()
        save_config(self.cfg)
        return False

    def _check_ytdlp(self):
        cmd = get_ytdlp_cmd()
        has_ffmpeg = shutil.which("ffmpeg") is not None

        if cmd:
            self._ytdlp_cmd = cmd
            self.ytdlp_ok = True
            if not has_ffmpeg:
                self._set_status("yt-dlp listo (⚠ falta ffmpeg)")
                self._log_direct("⚠ Nota: ffmpeg no está instalado. Se recomienda: sudo apt install ffmpeg\n")
            else:
                self._set_status("yt-dlp y ffmpeg listos ✓")
            return

        self._set_status("⚙ Instalando yt-dlp…")
        self._log_direct("yt-dlp no encontrado o dañado. Instalando automáticamente…\n")
        install_ytdlp(self._on_ytdlp_done)

    def _on_ytdlp_done(self, ok, method):
        if ok:
            self._ytdlp_cmd = get_ytdlp_cmd()
            self.ytdlp_ok = bool(self._ytdlp_cmd)
            self._set_status("yt-dlp listo ✓")
            self._log_direct(f"✅ yt-dlp instalado/reparado ({method})\n")
            self.toast("yt-dlp listo")
        else:
            self.ytdlp_ok = False
            self._set_status("⚠ yt-dlp no disponible")
            self._log_direct(
                "❌ No se pudo instalar yt-dlp.\n"
                "Ejecuta en terminal:\n"
                "  python3 -m pip install --user -U yt-dlp\n"
            )
        return False

    def _update_ytdlp(self, *_):
        self._log_direct("\n🔄 Actualizando yt-dlp…\n")
        self._start_pulse()

        def _do():
            updated = False
            methods = [
                [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "--user", "yt-dlp"],
                ["pip3", "install", "--quiet", "--upgrade", "--user", "yt-dlp"],
                ["pip3", "install", "--quiet", "--upgrade", "--break-system-packages", "yt-dlp"],
            ]
            for cmd in methods:
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                    if r.returncode == 0:
                        GLib.idle_add(self._log_direct, "✅ yt-dlp actualizado vía pip.\n")
                        updated = True
                        break
                except Exception:
                    pass

            if not updated:
                url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
                dest = USER_BIN / "yt-dlp"
                for dl in [["wget", "-qO", str(dest), url], ["curl", "-sSL", url, "-o", str(dest)]]:
                    try:
                        dest.unlink(missing_ok=True)
                        r = subprocess.run(dl, capture_output=True, timeout=60)
                        if r.returncode == 0 and dest.exists() and dest.stat().st_size > 10000:
                            dest.chmod(0o755)
                            if _is_working_ytdlp([str(dest)]):
                                GLib.idle_add(self._log_direct, f"✅ Binario actualizado en {dest}\n")
                                updated = True
                                break
                            dest.unlink(missing_ok=True)
                    except Exception:
                        pass

            if not updated:
                GLib.idle_add(self._log_direct, "❌ No se pudo actualizar.\n")
            else:
                self._ytdlp_cmd = get_ytdlp_cmd()
                self.ytdlp_ok = bool(self._ytdlp_cmd)
                if sel
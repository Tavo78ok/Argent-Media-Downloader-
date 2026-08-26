#!/usr/bin/env python3
"""
MediaDownloader v3.5 — GTK4 / libadwaita
Correcciones de compatibilidad:
 - Uso exclusivo de win.set_icon_name() para GTK4.
 - Compatibilidad con Adw.MessageDialog y Adw.AlertDialog según la versión instalada.
 - Actualización robusta de yt-dlp en espacio de usuario (~/.local/bin).
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
from pathlib import Path
from datetime import datetime

USER_BIN = Path.home() / ".local" / "bin"
USER_BIN.mkdir(parents=True, exist_ok=True)
os.environ["PATH"] = f"{USER_BIN}:/usr/local/bin:{os.environ.get('PATH', '')}"

APP_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#7c6af7"/>
      <stop offset="100%" stop-color="#a78bfa"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="14" fill="url(#bg)"/>
  <line x1="32" y1="10" x2="32" y2="38" stroke="white" stroke-width="5" stroke-linecap="round"/>
  <polyline points="18,26 32,42 46,26" fill="none" stroke="white" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="14" y="50" width="36" height="5" rx="2.5" fill="white" opacity="0.85"/>
</svg>"""

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
    return {"download_path": str(Path.home() / "Downloads"), "notify": True, "theme": "system"}

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

def install_ytdlp(callback):
    def _run():
        methods = [
            ["pip3", "install", "--quiet", "--user", "yt-dlp"],
            ["pip3", "install", "--quiet", "--break-system-packages", "yt-dlp"],
            ["pip",  "install", "--quiet", "yt-dlp"],
        ]
        for cmd in methods:
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=120)
                if r.returncode == 0 and shutil.which("yt-dlp"):
                    GLib.idle_add(callback, True, cmd[0])
                    return
            except Exception:
                pass

        url  = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
        dest = USER_BIN / "yt-dlp"
        for dl in [["wget", "-qO", str(dest), url], ["curl", "-sSL", url, "-o", str(dest)]]:
            try:
                r = subprocess.run(dl, capture_output=True, timeout=120)
                if r.returncode == 0 and dest.exists():
                    dest.chmod(0o755)
                    GLib.idle_add(callback, True, f"descarga directa a {dest.name}")
                    return
            except Exception:
                pass
        GLib.idle_add(callback, False, "")
    threading.Thread(target=_run, daemon=True).start()


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="MediaDownloader")
        self.set_default_size(740, 720)
        self.set_resizable(False)
        self.set_icon_name("io.github.MediaDownloader")

        self.cfg      = load_config()
        self.history  = load_history()
        self.process  = None
        self.downloading  = False
        self.ytdlp_ok     = False

        self._log_queue   = collections.deque()
        self._log_lock    = threading.Lock()
        self._flush_timer = None

        self._pl_total = 0
        self._pl_done  = 0

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

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
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

        # Modo
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

        # Calidad / formato
        opt_group = Adw.PreferencesGroup(title="Calidad y formato")
        main_box.append(opt_group)

        quality_row = Adw.ActionRow(title="Calidad")
        self.quality_combo = Gtk.DropDown.new_from_strings(["Mejor disponible", "1080p", "720p", "480p", "360p"])
        self.quality_combo.set_valign(Gtk.Align.CENTER)
        quality_row.add_suffix(self.quality_combo)
        opt_group.add(quality_row)

        format_row = Adw.ActionRow(title="Formato")
        self.format_combo = Gtk.DropDown.new_from_strings(["MP4", "MKV", "WEBM"])
        self.format_combo.set_valign(Gtk.Align.CENTER)
        format_row.add_suffix(self.format_combo)
        opt_group.add(format_row)

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
            subtitle=GLib.markup_escape_text(self.cfg.get("download_path", str(Path.home() / "Downloads"))))
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
        log_sw.set_min_content_height(130)
        log_sw.set_max_content_height(130)
        log_sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.log_buffer = Gtk.TextBuffer()
        self.log_view   = Gtk.TextView(
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
        action_box.set_margin_top(4)
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

        self._pulse_timer = None

    def _on_theme_changed(self, combo, _pspec):
        idx = combo.get_selected()
        themes = ["system", "dark", "light"]
        selected = themes[idx]
        self.cfg["theme"] = selected
        save_config(self.cfg)
        self._apply_theme(selected)

    def _check_ytdlp(self):
        has_ytdlp  = shutil.which("yt-dlp") is not None
        has_ffmpeg = shutil.which("ffmpeg") is not None

        if has_ytdlp:
            self.ytdlp_ok = True
            if not has_ffmpeg:
                self._set_status("yt-dlp listo (⚠ falta ffmpeg en el sistema)")
                self._log_direct("⚠ Nota: ffmpeg no está instalado. Se recomienda instalarlo con 'sudo apt install ffmpeg'.\n")
            else:
                self._set_status("yt-dlp y ffmpeg listos ✓")
            return

        self._set_status("⚙ Instalando yt-dlp en segundo plano…")
        self._log_direct("yt-dlp no encontrado. Instalando automáticamente…\n")
        install_ytdlp(self._on_ytdlp_done)

    def _on_ytdlp_done(self, ok, method):
        if ok:
            self.ytdlp_ok = True
            self._set_status("yt-dlp listo ✓")
            self._log_direct(f"✅ yt-dlp instalado ({method})\n")
            self.toast("yt-dlp instalado correctamente")
        else:
            self._set_status("⚠ yt-dlp no disponible")
            self._log_direct("❌ Instala manualmente en terminal: pip3 install --user yt-dlp\n")
        return False

    def _update_ytdlp(self, *_):
        self._log_direct("\n🔄 Buscando e instalando la versión más reciente de yt-dlp…\n")
        self._start_pulse()

        def _do():
            updated = False
            methods = [
                ["pip3", "install", "--quiet", "--upgrade", "--user", "yt-dlp"],
                ["pip3", "install", "--quiet", "--upgrade", "--break-system-packages", "yt-dlp"],
            ]
            for cmd in methods:
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if r.returncode == 0:
                        GLib.idle_add(self._log_direct, "✅ yt-dlp actualizado correctamente vía pip.\n")
                        updated = True
                        break
                except Exception:
                    pass

            if not updated:
                url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
                dest = USER_BIN / "yt-dlp"
                for dl in [["wget", "-qO", str(dest), url], ["curl", "-sSL", url, "-o", str(dest)]]:
                    try:
                        r = subprocess.run(dl, capture_output=True, timeout=60)
                        if r.returncode == 0 and dest.exists():
                            dest.chmod(0o755)
                            GLib.idle_add(self._log_direct, f"✅ Última versión de yt-dlp instalada en {dest}\n")
                            updated = True
                            break
                    except Exception:
                        pass

            if not updated:
                GLib.idle_add(self._log_direct, "❌ No se pudo actualizar. Verifica la conexión a internet.\n")

            GLib.idle_add(self._stop_pulse)
            GLib.idle_add(self.toast, "Proceso de actualización finalizado")

        threading.Thread(target=_do, daemon=True).start()

    def _set_status(self, text):
        self.status_row.set_title(GLib.markup_escape_text(text))
        return False

    def _log_direct(self, text):
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, text)
        self._scroll_log()
        return False

    def _log_enqueue(self, line):
        with self._log_lock:
            self._log_queue.append(line)

    def _flush_log(self):
        with self._log_lock:
            if not self._log_queue:
                return True
            text = "".join(self._log_queue)
            self._log_queue.clear()

        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, text)

        n = self.log_buffer.get_line_count()
        if n > LOG_MAX_LINES:
            s = self.log_buffer.get_start_iter()
            c = self.log_buffer.get_iter_at_line(n - LOG_MAX_LINES)
            self.log_buffer.delete(s, c)

        self._scroll_log()
        return True

    def _scroll_log(self):
        adj = self.log_view.get_parent().get_vadjustment()
        adj.set_value(adj.get_upper())

    def _log_clear(self):
        self.log_buffer.set_text("")

    def toast(self, msg):
        self.toast_overlay.add_toast(Adw.Toast(title=msg, timeout=3))

    def _start_pulse(self):
        self._stop_pulse()
        self._pulse_timer = GLib.timeout_add(80, self._pulse_cb)

    def _pulse_cb(self):
        self.progress_bar.pulse()
        return True

    def _stop_pulse(self):
        if self._pulse_timer:
            GLib.source_remove(self._pulse_timer)
            self._pulse_timer = None
        return False

    def _start_flush_timer(self):
        if self._flush_timer is None:
            self._flush_timer = GLib.timeout_add(LOG_FLUSH_MS, self._flush_log)

    def _stop_flush_timer(self):
        if self._flush_timer:
            GLib.source_remove(self._flush_timer)
            self._flush_timer = None
        self._flush_log()

    def _on_mode_toggle(self, btn):
        if not btn.get_active():
            return
        if self.toggle_video.get_active():
            self.format_combo.set_model(Gtk.StringList.new(["MP4", "MKV", "WEBM"]))
            self.quality_combo.set_model(Gtk.StringList.new(["Mejor disponible", "1080p", "720p", "480p", "360p"]))
        else:
            self.format_combo.set_model(Gtk.StringList.new(["MP3", "M4A", "OPUS", "FLAC", "WAV"]))
            self.quality_combo.set_model(Gtk.StringList.new(["Mejor disponible (320k)", "256k", "192k", "128k", "96k"]))

        self.format_combo.set_selected(0)
        self.quality_combo.set_selected(0)

    def _paste_url(self, *_):
        self.get_clipboard().read_text_async(None, self._on_clipboard_text)

    def _on_clipboard_text(self, clipboard, result):
        try:
            text = clipboard.read_text_finish(result)
            if text:
                self.url_entry.set_text(text.strip())
        except Exception:
            pass

    def _choose_dir(self, *_):
        Gtk.FileDialog(title="Seleccionar carpeta de destino").select_folder(self, None, self._on_folder_chosen)

    def _on_folder_chosen(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                self.dest_row.set_subtitle(GLib.markup_escape_text(path))
                self.cfg["download_path"] = path
                save_config(self.cfg)
        except Exception:
            pass

    def _save_prefs(self, *_):
        self.cfg["notify"] = self.notif_switch.get_active()
        save_config(self.cfg)
        return False

    def _get_mode(self):
        return "video" if self.toggle_video.get_active() else "audio"

    def _get_quality(self):
        mode = self._get_mode()
        idx = self.quality_combo.get_selected()
        if mode == "video":
            labels = ["best", "1080", "720", "480", "360"]
        else:
            labels = ["best", "256k", "192k", "128k", "96k"]
        return labels[min(idx, len(labels) - 1)]

    def _get_format(self):
        item = self.format_combo.get_selected_item()
        return item.get_string().lower() if item else "mp4"

    def _build_cmd(self, url):
        out  = self.cfg.get("download_path", str(Path.home() / "Downloads"))
        mode = self._get_mode()
        q    = self._get_quality()
        fmt  = self._get_format()
        pl   = self.pl_switch.get_active()

        yt_exec = shutil.which("yt-dlp") or "yt-dlp"

        cmd = [
            yt_exec,
            "--newline",
            "--user-agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "--extractor-args", "youtube:player_client=android,web"
        ]

        if pl:
            cmd += ["--ignore-errors", "--yes-playlist"]
            tpl = f"{out}/%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s"
        else:
            cmd += ["--no-playlist"]
            tpl = f"{out}/%(title)s.%(ext)s"

        has_ffmpeg = shutil.which("ffmpeg") is not None

        if mode == "audio":
            cmd += ["-x", "--audio-format", fmt]
            if q != "best":
                cmd += ["--audio-quality", q]
        else:
            if has_ffmpeg:
                f_sel = ("bestvideo+bestaudio/best" if q == "best"
                         else f"bestvideo[height<={q}]+bestaudio/best[height<={q}]/best")
                cmd += ["-f", f_sel, "--merge-output-format", fmt]
            else:
                f_sel = "best" if q == "best" else f"best[height<={q}]/best"
                cmd += ["-f", f_sel]

        cmd += ["-o", tpl, url]
        return cmd, fmt

    def _start_download(self, *_):
        yt_exec = shutil.which("yt-dlp")
        if not self.ytdlp_ok and not yt_exec:
            self.toast("yt-dlp aún no está listo, espera unos segundos")
            return
        url = self.url_entry.get_text().strip()
        if not url:
            self.toast("Ingresa una URL primero")
            return
        if not url.startswith(("http://", "https://")):
            self.toast("La URL debe comenzar con http:// o https://")
            return

        os.makedirs(self.cfg.get("download_path", str(Path.home() / "Downloads")), exist_ok=True)

        self.downloading  = True
        self.dl_btn.set_sensitive(False)
        self.cancel_btn.set_sensitive(True)
        self._log_clear()
        self._set_status("Iniciando descarga…")
        self._pl_total = 0
        self._pl_done  = 0
        self.progress_bar.set_fraction(0)
        self._current_url = url

        cmd, fmt = self._build_cmd(url)
        self._current_fmt = fmt
        self._current_pl  = self.pl_switch.get_active()

        self._log_direct("$ " + " ".join(cmd) + "\n\n")

        if not self._current_pl:
            self._start_pulse()

        self._start_flush_timer()
        threading.Thread(target=self._run, args=(cmd,), daemon=True).start()

    _RE_PL = re.compile(r"\[download\] Downloading item (\d+) of (\d+)")

    def _run(self, cmd):
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1)

            for line in self.process.stdout:
                self._log_enqueue(line)

                m = self._RE_PL.search(line)
                if m:
                    done  = int(m.group(1))
                    total = int(m.group(2))
                    GLib.idle_add(self._update_pl_progress, done, total)

            self.process.wait()
            GLib.idle_add(self._finish, self.process.returncode)

        except FileNotFoundError:
            self._log_enqueue("\n❌ Ejecutable 'yt-dlp' no encontrado en el PATH.\n")
            GLib.idle_add(self._finish, 1)

    def _update_pl_progress(self, done, total):
        self._pl_done  = done
        self._pl_total = total
        self.progress_bar.set_fraction(done / total if total else 0)
        self._set_status(f"Descargando {done}/{total}…")
        return False

    def _finish(self, rc):
        self._stop_flush_timer()
        self._stop_pulse()
        self.progress_bar.set_fraction(1.0 if rc == 0 else 0)
        self.downloading = False
        self.dl_btn.set_sensitive(True)
        self.cancel_btn.set_sensitive(False)

        url = getattr(self, "_current_url", "")
        fmt = getattr(self, "_current_fmt", "")
        pl  = getattr(self, "_current_pl",  False)

        if rc == 0:
            total = self._pl_total
            msg   = (f"✓ {total} archivos descargados" if pl and total else "✓ Descarga completada")
            self._set_status(msg)
            self._log_direct(f"\n✅ {msg}\n")
            self.toast(msg)
            self.history.append({
                "url":  url, "mode": self._get_mode(), "fmt": fmt,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "dest": self.cfg.get("download_path", ""),
            })
            save_history(self.history)
            if self.notif_switch.get_active():
                send_notification("MediaDownloader", f"{msg} ({fmt.upper()})")
        elif rc in (-9, -15):
            self._set_status("Cancelado")
        else:
            self._set_status(f"❌ Error (código {rc})")
            self._log_direct(f"\n❌ Error en la descarga (código {rc}). Revisa el log de arriba.\n")
            self.toast(f"Error en la descarga (código {rc})")
            if self.notif_switch.get_active():
                send_notification("MediaDownloader", "La descarga falló")
        return False

    def _cancel(self, *_):
        if self.process and self.downloading:
            self.process.terminate()
            self._log_direct("\n⚠ Descarga cancelada.\n")

    def _show_history(self, *_):
        win = Adw.Window(title="Historial", transient_for=self, modal=True)
        win.set_default_size(680, 420)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        win.set_content(box)

        hdr = Adw.HeaderBar()
        hdr.set_title_widget(Gtk.Label(label="Historial de descargas"))
        box.append(hdr)

        if not self.history:
            box.append(Adw.StatusPage(
                title="Sin historial",
                description="Las descargas completadas aparecerán aquí",
                icon_name="document-open-recent-symbolic",
                vexpand=True))
        else:
            scroll = Gtk.ScrolledWindow(vexpand=True)
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            box.append(scroll)

            list_box = Gtk.ListBox()
            list_box.add_css_class("boxed-list")
            list_box.set_margin_start(16)
            list_box.set_margin_end(16)
            list_box.set_margin_top(16)
            list_box.set_margin_bottom(8)
            list_box.set_selection_mode(Gtk.SelectionMode.NONE)
            scroll.set_child(list_box)

            for entry in reversed(self.history):
                row = Adw.ActionRow(
                    title=GLib.markup_escape_text(entry.get("url", "")),
                    subtitle=GLib.markup_escape_text(
                              f"{entry.get('date','')}  •  "
                              f"{entry.get('mode','').upper()}  •  "
                              f"{entry.get('fmt','').upper()}"))
                list_box.append(row)

            btn_row = Gtk.Box(spacing=8)
            btn_row.set_margin_start(16)
            btn_row.set_margin_end(16)
            btn_row.set_margin_bottom(16)
            btn_row.set_margin_top(8)
            box.append(btn_row)

            clear_btn = Gtk.Button(label="🗑  Borrar historial")
            clear_btn.add_css_class("destructive-action")
            clear_btn.add_css_class("pill")

            def clear(*_):
                if hasattr(Adw, "AlertDialog"):
                    d = Adw.AlertDialog(heading="¿Borrar historial?", body="Esta acción no se puede deshacer.")
                    d.add_response("cancel", "Cancelar")
                    d.add_response("delete", "Borrar")
                    d.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
                    def on_resp(dlg, resp):
                        if resp == "delete":
                            self.history.clear()
                            save_history(self.history)
                            win.close()
                            self.toast("Historial borrado")
                    d.connect("response", on_resp)
                    d.present(win)
                else:
                    d = Adw.MessageDialog(transient_for=win, heading="¿Borrar historial?", body="Esta acción no se puede deshacer.")
                    d.add_response("cancel", "Cancelar")
                    d.add_response("delete", "Borrar")
                    d.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
                    def on_resp(dlg, resp):
                        if resp == "delete":
                            self.history.clear()
                            save_history(self.history)
                            win.close()
                            self.toast("Historial borrado")
                    d.connect("response", on_resp)
                    d.present()

            clear_btn.connect("clicked", clear)
            btn_row.append(clear_btn)

        win.present()


class MediaDownloaderApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.github.MediaDownloader",
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        win = MainWindow(self)
        win.present()


if __name__ == "__main__":
    import sys
    app = MediaDownloaderApp()
    sys.exit(app.run(sys.argv))
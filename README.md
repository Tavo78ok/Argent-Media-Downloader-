## Argent Media Downloader

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-7c6af7?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Python-3.8+-3776ab?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/GTK4-libadwaita-4a86cf?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Linux-Debian%2FUbuntu-e95420?style=for-the-badge&logo=linux&logoColor=white"/>
  <img src="https://img.shields.io/badge/license-MIT-34d399?style=for-the-badge"/>
</p>

<p align="center">
  Descargador de video y música para Linux con interfaz nativa GTK4 + libadwaita.<br>
  Compatible con YouTube, TikTok, SoundCloud, Vimeo, Twitch, Instagram, Facebook y más de 1000 sitios.
</p>

---

## Capturas

> *Interfaz nativa GTK4/libadwaita — se adapta automáticamente al tema del sistema (claro u oscuro).*

---

## Características

- 🎬 **Descarga de video** en MP4, MKV y WEBM
- 🎵 **Descarga de solo audio** en MP3, M4A, OPUS, FLAC y WAV
- 🎞 **Soporte de playlists completas**
- 📋 **Historial de descargas** persistente
- 🔔 **Notificaciones de escritorio** al completar cada descarga
- 🔄 **Actualización de yt-dlp** desde la propia interfaz
- ⚙ **Instalación automática de yt-dlp** al primer arranque
- 🎨 **Interfaz GTK4 + libadwaita** integrada con el tema del sistema
- 🖼 **Icono SVG** incluido, visible en dock y menú de aplicaciones

---

## Requisitos

| Dependencia | Versión mínima | Notas |
|---|---|---|
| Python | 3.8+ | Incluido en la mayoría de distros |
| GTK4 | 4.0+ | `gir1.2-gtk-4.0` |
| libadwaita | 1.0+ | `gir1.2-adw-1` |
| python3-gi | — | Bindings GObject para Python |
| ffmpeg | — | Para conversión de formatos |
| yt-dlp | — | Se instala automáticamente al primer uso |

---

## Instalación

### Opción A — Paquete .deb (recomendado)

Descarga el `.deb` desde la sección [Releases](../../releases/latest) e instala con:

```bash
sudo dpkg -i media-downloader_3.0.0_all.deb
sudo apt-get install -f -y
```

El paquete instala todas las dependencias automáticamente. `yt-dlp` se descarga la primera vez que abres la app.

### Opción B — Ejecutar directamente

```bash
# 1. Instalar dependencias del sistema
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 ffmpeg

# 2. Instalar yt-dlp
pip3 install yt-dlp

# 3. Ejecutar
python3 media_downloader.py
```

### Opción C — Clonar el repositorio

```bash
git clone https://github.com/Tavo78ok/media-downloader.git
cd media-downloader
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 ffmpeg
pip3 install yt-dlp
python3 media_downloader.py
```

---

## Uso

1. Pega la URL del video, canción o lista de reproducción
2. Elige **Video** o **Solo Audio**
3. Selecciona calidad y formato
4. Activa **"Descargar lista completa"** si es una playlist
5. Elige la carpeta de destino
6. Pulsa **Descargar**

### Actualizar yt-dlp

Desde la propia interfaz, usa el botón **"Actualizar yt-dlp"** en la barra superior.
O desde la terminal:

```bash
yt-dlp -U
```

---

## Plataformas compatibles (muestra)

YouTube · SoundCloud · TikTok · Twitter/X · Vimeo · Twitch · Facebook · Instagram · Reddit · Dailymotion · Bandcamp · Mixcloud · y más de 1000 sitios adicionales.

Lista completa: [yt-dlp/supportedsites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

---

## Desinstalar

```bash
sudo apt remove media-downloader       # desinstala la app
sudo apt purge media-downloader        # desinstala y elimina todos los archivos
```

---

## Estructura del proyecto

```
media-downloader/
├── media_downloader.py       # Código fuente principal (GTK4/libadwaita)
├── README.md
└── packaging/
    └── build-deb.sh          # Script para construir el .deb
```

---

## Tecnologías

- [Python 3](https://python.org) — lenguaje principal
- [GTK4](https://gtk.org) + [libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/) — interfaz gráfica nativa
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — motor de descarga
- [ffmpeg](https://ffmpeg.org) — conversión y mezcla de streams

---

## Licencia

MIT © [Tavo78ok](https://github.com/Tavo78ok)

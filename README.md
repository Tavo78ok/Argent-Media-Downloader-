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
<img width="1440" height="900" alt="Captura de pantalla de 2026-08-31 16-39-35" src="https://github.com/user-attachments/assets/1a2ee8d9-f00e-49f7-867e-d231cbe6b233" />

<img width="1440" height="900" alt="Captura de pantalla de 2026-08-31 16-39-49" src="https://github.com/user-attachments/assets/544f7d1e-367d-468e-a077-c06012cb6c01" />


<img width="1440" height="900" alt="Captura de pantalla de 2026-08-31 16-40-49" src="https://github.com/user-attachments/assets/651fbb2c-4f6b-4a36-a239-b745732b2a5c" />

<img width="1440" height="900" alt="Captura de pantalla de 2026-08-31 16-41-10" src="https://github.com/user-attachments/assets/1b99eb3f-bdb1-4cb7-aba6-f579fdbfcbe6" />

<img width="1440" height="900" alt="Captura de pantalla de 2026-08-31 16-41-22" src="https://github.com/user-attachments/assets/663fb097-3fb6-4b6b-b767-facb333c8d7c" />

<img width="1440" height="900" alt="Captura de pantalla de 2026-08-31 16-41-49" src="https://github.com/user-attachments/assets/02d1e565-6f1d-471f-bec5-f3ef3952fcf7" />

<img width="1440" height="900" alt="Captura de pantalla de 2026-08-31 16-42-01" src="https://github.com/user-attachments/assets/ff73881f-55bd-412d-abcb-1a2d58d91071" />

<img width="740" height="720" alt="Captura de pantalla de 2026-08-31 16-42-28" src="https://github.com/user-attachments/assets/cec1206c-b550-42fe-86ad-bd4b475e681e" />

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

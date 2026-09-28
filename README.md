# Argent Media Downloader

**Descarga video y música de cualquier plataforma** con una interfaz moderna y sencilla basada en GTK4 + libadwaita.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![GTK](https://img.shields.io/badge/GTK-4-green?logo=gnome)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Características

- Interfaz limpia y nativa (libadwaita)
- Soporte para **video** y **solo audio**
- Descarga de **playlists** completas
- Selección de calidad y formato
- **Subtítulos** (español + automáticos) en formato `.srt`
- **Incrustar miniatura y metadatos** en el archivo
- **SponsorBlock** (elimina anuncios, intros, sponsors, etc.)
- **Cookies del navegador** (Firefox / Chrome / Chromium) para contenido con restricción de edad
- Progreso en tiempo real + log detallado
- Historial de descargas
- Notificaciones de escritorio
- Tema claro / oscuro / sistema
- Instalación y actualización automática de `yt-dlp`
- Detección y reparación de binarios corruptos

---

## Capturas

<img width="1440" height="900" alt="Captura de pantalla de 2026-09-26 14-25-24" src="https://github.com/user-attachments/assets/005aa9e4-6b5b-4208-9232-ce3e48ab17fe" />
<img width="1440" height="900" alt="Captura de pantalla de 2026-09-26 14-25-44" src="https://github.com/user-attachments/assets/a2a716cf-a001-4dd1-a817-defffada9afa" />
<img width="1440" height="900" alt="Captura de pantalla de 2026-09-26 14-26-22" src="https://github.com/user-attachments/assets/975e9bbd-b126-4710-aac3-d2425600b9ea" />
<img width="1440" height="900" alt="Captura de pantalla de 2026-09-26 14-26-45" src="https://github.com/user-attachments/assets/6940f5de-0eac-491a-a805-6b90f2694af0" />
<img width="1440" height="900" alt="Captura de pantalla de 2026-09-26 14-27-06" src="https://github.com/user-attachments/assets/8c0edb63-5305-4c94-a7ef-4e2d06af48ef" />
<img width="1440" height="900" alt="Captura de pantalla de 2026-09-26 14-27-40" src="https://github.com/user-attachments/assets/decb81f7-1d9d-4f13-b822-e895a9bd0466" />


---

## Requisitos

- Linux (probado en Cinnamon, GNOME, etc.)
- Python 3.10 o superior
- GTK 4 + libadwaita
- `ffmpeg` (recomendado para mejor calidad y fusión de audio/video)
- `yt-dlp` (se instala automáticamente si falta)

### Instalar dependencias del sistema (Debian/Ubuntu/ArgentOS)

```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 ffmpeg
```

---

## Instalación

1. Clona el repositorio o descarga el archivo:

```bash
git clone https://github.com/Tavo78ok/MediaDownloader.git
cd MediaDownloader
```

2. (Opcional pero recomendado) Instala/actualiza yt-dlp:

```bash
python3 -m pip install --user -U yt-dlp
```

3. Ejecuta la aplicación:

```bash
python3 media_downloader.py
```

---

## Uso

1. Pega la URL del video, canción o lista.
2. Elige **Video** o **Solo Audio**.
3. Selecciona calidad y formato.
4. Activa las opciones avanzadas que necesites (subtítulos, SponsorBlock, cookies, etc.).
5. Elige la carpeta de destino.
6. Pulsa **Descargar**.

Puedes cancelar la descarga en cualquier momento.

---

## Opciones avanzadas

| Opción | Descripción |
|--------|-------------|
| **Descargar subtítulos** | Baja subtítulos en español + automáticos y los convierte a `.srt` |
| **Incrustar miniatura y metadatos** | Guarda la carátula y la información dentro del archivo |
| **SponsorBlock** | Elimina automáticamente anuncios, intros, outros y sponsors |
| **Cookies del navegador** | Usa las cookies de Firefox, Chrome o Chromium (útil para contenido restringido) |

Todas las preferencias se guardan automáticamente.

---

## Actualizar yt-dlp

Dentro de la aplicación hay un botón **Actualizar yt-dlp** en la barra superior.  
También puedes actualizarlo manualmente:

```bash
python3 -m pip install --user -U yt-dlp
```

---

## Archivos de configuración

- Configuración: `~/.config/media-downloader/config.json`
- Historial: `~/.config/media-downloader/history.json`

---

## Solución de problemas

### Error: "Formato de ejecutable incorrecto"
```bash
rm -f ~/.local/bin/yt-dlp
python3 -m pip install --user -U yt-dlp
```

### Falta ffmpeg
```bash
sudo apt install ffmpeg
```

### No descarga de YouTube
- Actualiza yt-dlp
- Prueba activar las cookies del navegador
- Asegúrate de tener `node` instalado (mejora la extracción)

---

## Tecnologías

- **Python 3**
- **GTK 4 + libadwaita**
- **yt-dlp** (motor de descarga)
- **ffmpeg** (procesamiento de medios)

---

## Licencia

Mit License. Puedes usarlo, modificarlo y distribuirlo libremente.

---

## Créditos

Desarrollado con ❤️ usando [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Colaborar:

**🇦🇷 Desde Argentina (Mercado Pago):**
- 💳 Alias MP: `tavo.78.ok`
- 🔗 CVU: `0000003100099682904311`

**🌎 Desde el exterior (PayPal):**
- 💙 [paypal.me/GustavoCuevas582](https://paypal.me/GustavoCuevas582)

---

¿Encontraste un bug o tienes una idea? ¡Abre un issue!

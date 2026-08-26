#!/usr/bin/env bash
#
# build-appimage.sh — Empaqueta MediaDownloader (GTK4/libadwaita) como AppImage
#
# Uso:
#   ./build-appimage.sh [version]
#
# Ejemplo:
#   ./build-appimage.sh 3.5
#
# IMPORTANTE — sobre las dependencias de GTK4/libadwaita:
#   Empaquetar GTK4 + libadwaita + PyGObject de forma 100% autocontenida dentro
#   de un AppImage es extremadamente frágil (decenas de .so, typelibs de
#   GObject-Introspection, temas de iconos, GSettings schemas, etc.), y suele
#   romperse entre distribuciones. Por eso este script sigue el enfoque que
#   usan la mayoría de apps GTK4/Adwaita distribuidas como AppImage:
#     -> el AppImage empaqueta el CÓDIGO de la app,
#     -> pero usa el python3 + GTK4 + libadwaita YA INSTALADOS en el sistema
#        anfitrión (algo normal en cualquier distro con escritorio GNOME).
#   AppRun verifica esas dependencias al arrancar y, si faltan, muestra
#   instrucciones claras de instalación en vez de fallar en silencio.
#
# Dependencias necesarias en la MÁQUINA DONDE COMPILAS este AppImage:
#   - bash, sed, wget o curl
#   - (nada más: appimagetool se descarga automáticamente si falta)
#
# Dependencias necesarias en la MÁQUINA DONDE SE EJECUTA el AppImage:
#   - python3
#   - python3-gi (PyGObject) + GTK4 + libadwaita (gir1.2-gtk-4.0, gir1.2-adw-1)
#   - ffmpeg (opcional, recomendado para conversión/merge de formatos)
#   - yt-dlp (si no está, la propia app intenta instalarlo sola vía pip/descarga directa)

set -euo pipefail

# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------
APP_NAME="MediaDownloader"
APP_ID="io.github.MediaDownloader"
BIN_NAME="media-downloader"
VERSION="${1:-3.5}"
ARCH="$(uname -m)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_PY="${SCRIPT_DIR}/media-downloader.py"
BUILD_DIR="${SCRIPT_DIR}/build"
APPDIR="${BUILD_DIR}/${APP_NAME}.AppDir"
TOOLS_DIR="${SCRIPT_DIR}/tools"
OUTPUT="${SCRIPT_DIR}/${APP_NAME}-${VERSION}-${ARCH}.AppImage"

log()  { printf '\033[1;34m[build]\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m[aviso]\033[0m %s\n' "$1" >&2; }
die()  { printf '\033[1;31m[error]\033[0m %s\n' "$1" >&2; exit 1; }

# --------------------------------------------------------------------------
# Comprobaciones previas
# --------------------------------------------------------------------------
[ -f "$SRC_PY" ] || die "No se encontró '${SRC_PY}'. Coloca este script junto a media-downloader.py."

DOWNLOADER=""
if command -v wget >/dev/null 2>&1; then
    DOWNLOADER="wget -q -O"
elif command -v curl >/dev/null 2>&1; then
    DOWNLOADER="curl -sSL -o"
else
    die "Necesitas 'wget' o 'curl' instalado para descargar appimagetool."
fi

# --------------------------------------------------------------------------
# 1. Preparar estructura del AppDir
# --------------------------------------------------------------------------
log "Preparando AppDir en ${APPDIR}"
rm -rf "$BUILD_DIR"
mkdir -p \
    "${APPDIR}/usr/bin" \
    "${APPDIR}/usr/share/applications" \
    "${APPDIR}/usr/share/icons/hicolor/scalable/apps" \
    "${APPDIR}/usr/share/metainfo"

# --------------------------------------------------------------------------
# 2. Copiar el script de la aplicación
# --------------------------------------------------------------------------
log "Copiando ${BIN_NAME}.py"
cp "$SRC_PY" "${APPDIR}/usr/bin/${BIN_NAME}.py"
chmod +x "${APPDIR}/usr/bin/${BIN_NAME}.py"

# --------------------------------------------------------------------------
# 3. Extraer el icono SVG embebido en el propio script (APP_ICON_SVG)
# --------------------------------------------------------------------------
log "Extrayendo icono SVG desde el código fuente"
ICON_SVG="${APPDIR}/usr/share/icons/hicolor/scalable/apps/${APP_ID}.svg"

sed -n '/^APP_ICON_SVG = """/,/"""$/p' "$SRC_PY" \
    | sed -e '1s/^APP_ICON_SVG = """//' -e '$s/"""$//' \
    > "$ICON_SVG"

if [ ! -s "$ICON_SVG" ]; then
    warn "No se pudo extraer APP_ICON_SVG del script; usando icono de repuesto genérico."
    cat > "$ICON_SVG" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#7c6af7"/>
  <text x="32" y="40" font-size="28" text-anchor="middle" fill="white">MD</text>
</svg>
SVG
fi

# Copia del icono en la raíz del AppDir (requerido por appimagetool/thumbnailers)
cp "$ICON_SVG" "${APPDIR}/${APP_ID}.svg"

# --------------------------------------------------------------------------
# 4. Archivo .desktop
# --------------------------------------------------------------------------
log "Generando archivo .desktop"
DESKTOP_FILE="${APPDIR}/usr/share/applications/${APP_ID}.desktop"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=${APP_NAME}
GenericName=Descargador de video y audio
Comment=Descarga video y música de cualquier plataforma con yt-dlp
Exec=${BIN_NAME}
Icon=${APP_ID}
Categories=AudioVideo;Network;Utility;
Terminal=false
StartupNotify=true
EOF
cp "$DESKTOP_FILE" "${APPDIR}/${APP_ID}.desktop"

# --------------------------------------------------------------------------
# 5. AppRun — punto de entrada del AppImage
# --------------------------------------------------------------------------
log "Generando AppRun"
cat > "${APPDIR}/AppRun" <<'APPRUN'
#!/usr/bin/env bash
set -euo pipefail

HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"

# Localizar un intérprete python3 del sistema anfitrión
PYTHON_BIN="$(command -v python3 || true)"
if [ -z "${PYTHON_BIN}" ]; then
    echo "----------------------------------------------------------------------" >&2
    echo "No se encontró 'python3' en el sistema. Instálalo con tu gestor de" >&2
    echo "paquetes (ej: sudo apt install python3) y vuelve a intentarlo." >&2
    echo "----------------------------------------------------------------------" >&2
    exit 1
fi

# Verificar GTK4 / libadwaita / PyGObject en el sistema anfitrión
if ! "${PYTHON_BIN}" - <<'PYCHECK' >/dev/null 2>&1
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk
PYCHECK
then
    echo "----------------------------------------------------------------------" >&2
    echo "Faltan dependencias del sistema (GTK4 / libadwaita / PyGObject)." >&2
    echo "Instálalas según tu distribución:" >&2
    echo "  Debian/Ubuntu : sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1" >&2
    echo "  Fedora        : sudo dnf install python3-gobject gtk4 libadwaita" >&2
    echo "  Arch Linux    : sudo pacman -S python-gobject gtk4 libadwaita" >&2
    echo "  openSUSE      : sudo zypper install python3-gobject gtk4 libadwaita" >&2
    echo "----------------------------------------------------------------------" >&2
    exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "Aviso: 'ffmpeg' no está instalado. Algunas conversiones de formato" >&2
    echo "pueden fallar. Instálalo con 'sudo apt install ffmpeg' (o el" >&2
    echo "equivalente en tu distro) para funcionalidad completa." >&2
fi

exec "${PYTHON_BIN}" "${HERE}/usr/bin/media-downloader.py" "$@"
APPRUN
chmod +x "${APPDIR}/AppRun"

# --------------------------------------------------------------------------
# 6. Descargar appimagetool si hace falta
# --------------------------------------------------------------------------
mkdir -p "$TOOLS_DIR"
APPIMAGETOOL="${TOOLS_DIR}/appimagetool-${ARCH}.AppImage"

if [ ! -x "$APPIMAGETOOL" ]; then
    log "Descargando appimagetool (${ARCH})"
    APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
    eval "$DOWNLOADER" "\"$APPIMAGETOOL\"" "\"$APPIMAGETOOL_URL\"" \
        || die "No se pudo descargar appimagetool desde ${APPIMAGETOOL_URL}"
    chmod +x "$APPIMAGETOOL"
fi

# --------------------------------------------------------------------------
# 7. Construir el AppImage
# --------------------------------------------------------------------------
log "Construyendo ${OUTPUT}"
cd "$SCRIPT_DIR"

# ARCH es requerido por appimagetool cuando no se detecta automáticamente
ARCH="$ARCH" "$APPIMAGETOOL" "$APPDIR" "$OUTPUT" \
    || die "appimagetool falló. Revisa el log de arriba."

chmod +x "$OUTPUT"

log "Listo ✓  →  ${OUTPUT}"
echo
echo "Para ejecutarlo:"
echo "  ./$(basename "$OUTPUT")"
echo
echo "Nota: el AppImage usa GTK4/libadwaita/python3-gi del sistema anfitrión."
echo "Si el equipo destino no los tiene instalados, AppRun mostrará las"
echo "instrucciones de instalación necesarias al ejecutarse."

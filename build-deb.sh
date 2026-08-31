#!/bin/bash
# Script de empaquetado .deb para MediaDownloader con caché de iconos

set -e

PKG_NAME="media-downloader"
VERSION="3.4-2"
ARCH="all"
APP_ID="io.github.MediaDownloader"
BUILD_DIR="build_deb/${PKG_NAME}_${VERSION}_${ARCH}"

echo "📦 Creando estructura del paquete Debian..."
rm -rf build_deb
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/share/media-downloader"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps"

# 1. Copiar script Python
cp media_downloader.py "${BUILD_DIR}/usr/share/media-downloader/media_downloader.py"
chmod 755 "${BUILD_DIR}/usr/share/media-downloader/media_downloader.py"

# 2. Crear ejecutable en /usr/bin
cat << 'EOF' > "${BUILD_DIR}/usr/bin/media-downloader"
#!/bin/bash
exec python3 /usr/share/media-downloader/media_downloader.py "$@"
EOF
chmod 755 "${BUILD_DIR}/usr/bin/media-downloader"

# 3. Crear acceso directo (.desktop)
cat << EOF > "${BUILD_DIR}/usr/share/applications/${APP_ID}.desktop"
[Desktop Entry]
Name=MediaDownloader
Comment=Descarga video y música de cualquier plataforma
Exec=media-downloader
Icon=${APP_ID}
Terminal=false
Type=Application
Categories=Utility;AudioVideo;Network;
StartupWMClass=${APP_ID}
EOF

# 4. Extraer el icono SVG embebido con el nombre del App ID
python3 -c "
import re
with open('media_downloader.py') as f:
    code = f.read()
m = re.search(r'APP_ICON_SVG = \"\"\"(.*?)\"\"\"', code, re.DOTALL)
if m:
    with open('${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps/${APP_ID}.svg', 'w') as out:
        out.write(m.group(1))
"

# 5. Archivo de control de Debian
cat << EOF > "${BUILD_DIR}/DEBIAN/control"
Package: ${PKG_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: python3, python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1, ffmpeg
Maintainer: MediaDownloader <media.downloader@local>
Description: Descargador de audio y video ligero basado en GTK4 y Libadwaita.
EOF

# 6. Script post-instalación para actualizar la caché de iconos de Linux
cat << 'EOF' > "${BUILD_DIR}/DEBIAN/postinst"
#!/bin/sh
set -e
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true
fi
EOF
chmod 755 "${BUILD_DIR}/DEBIAN/postinst"

# 7. Script post-remoción
cat << 'EOF' > "${BUILD_DIR}/DEBIAN/postrm"
#!/bin/sh
set -e
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true
fi
EOF
chmod 755 "${BUILD_DIR}/DEBIAN/postrm"

echo "🔨 Compilando paquete .deb..."
dpkg-deb --build "${BUILD_DIR}"

DEB_OUT="media-downloader_${VERSION}_all.deb"
mv "build_deb/${PKG_NAME}_${VERSION}_${ARCH}.deb" "./${DEB_OUT}"
rm -rf build_deb

echo "✅ ¡Empaquetado completado! Tu archivo es: ${DEB_OUT}"
#!/usr/bin/env bash
# ============================================================================
# Instalador del Gateway Edge de Ho smartvision en una Raspberry Pi (Debian/RPi OS)
# Uso:  sudo bash install.sh
# ============================================================================
set -euo pipefail

INSTALL_DIR="/opt/ho-smartvision-gateway"
GO2RTC_VERSION="v1.9.4"

echo ">> Instalando dependencias del sistema…"
apt-get update
apt-get install -y python3 python3-venv python3-pip curl libxml2-dev libxslt1-dev

echo ">> Copiando el gateway a ${INSTALL_DIR}…"
mkdir -p "${INSTALL_DIR}"
cp -r ./*.py requirements.txt "${INSTALL_DIR}/"
[ -f .env ] && cp .env "${INSTALL_DIR}/.env" || cp .env.example "${INSTALL_DIR}/.env"

echo ">> Creando entorno virtual e instalando dependencias de Python…"
python3 -m venv "${INSTALL_DIR}/.venv"
"${INSTALL_DIR}/.venv/bin/pip" install --upgrade pip
"${INSTALL_DIR}/.venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

echo ">> Instalando go2rtc (${GO2RTC_VERSION})…"
ARCH=$(uname -m)
case "${ARCH}" in
  aarch64) BIN="go2rtc_linux_arm64" ;;
  armv7l)  BIN="go2rtc_linux_arm" ;;
  x86_64)  BIN="go2rtc_linux_amd64" ;;
  *) echo "Arquitectura no soportada: ${ARCH}"; exit 1 ;;
esac
curl -L -o /usr/local/bin/go2rtc \
  "https://github.com/AlexxIT/go2rtc/releases/download/${GO2RTC_VERSION}/${BIN}"
chmod +x /usr/local/bin/go2rtc
mkdir -p /etc/go2rtc
[ -f /etc/go2rtc/go2rtc.yaml ] || cp go2rtc.example.yaml /etc/go2rtc/go2rtc.yaml

echo ">> Instalando servicios systemd…"
cat >/etc/systemd/system/go2rtc.service <<'EOF'
[Unit]
Description=go2rtc
After=network-online.target
Wants=network-online.target
[Service]
ExecStart=/usr/local/bin/go2rtc -config /etc/go2rtc/go2rtc.yaml
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF
cp systemd/ho-smartvision-gateway.service /etc/systemd/system/ho-smartvision-gateway.service

systemctl daemon-reload
systemctl enable --now go2rtc.service
systemctl enable --now ho-smartvision-gateway.service

echo ">> Listo. Revisa los logs con:"
echo "   journalctl -u ho-smartvision-gateway -f"
echo "   journalctl -u go2rtc -f"
echo ">> IMPORTANTE: edita ${INSTALL_DIR}/.env con tus valores reales y reinicia:"
echo "   sudo systemctl restart ho-smartvision-gateway"

#!/bin/bash
# ============================================================
# server-setup.sh — Первичная настройка VPS Ubuntu 22.04
#
# Для PUBLIC репозитория — запуск напрямую с GitHub:
#   curl -fsSL https://raw.githubusercontent.com/ВАШ_ЛОГИН/64dao/main/deploy/scripts/server-setup.sh | bash
#
# С клонированием репозитория:
#   bash server-setup.sh --repo https://github.com/ВАШ_ЛОГИН/64dao.git
#
# Если код уже на сервере:
#   bash /var/www/64dao/deploy/scripts/server-setup.sh
# ============================================================

set -euo pipefail

REPO_URL=""
APP_DIR="/var/www/64dao"
APP_USER="dao64"
DOMAIN="64dao.ru"
BACKUP_DIR="/var/backups/64dao"

while [[ $# -gt 0 ]]; do
    case $1 in
        --repo) REPO_URL="$2"; shift 2 ;;
        *) shift ;;
    esac
done

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*"; exit 1; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
info() { echo -e "${BLUE}→${NC} $*"; }
step() { echo -e "\n${BLUE}═══ $* ═══${NC}"; }

[ "$(id -u)" -eq 0 ] || err "Запустите от root: sudo bash server-setup.sh"

step "1/9 Обновление системы"
export DEBIAN_FRONTEND=noninteractive
apt update -qq && apt upgrade -y -qq
apt install -y -qq curl wget git unzip htop iotop ufw fail2ban \
    software-properties-common apt-transport-https ca-certificates gnupg lsb-release
ok "Система обновлена"

step "2/9 Системный пользователь ${APP_USER}"
if ! id "${APP_USER}" &>/dev/null; then
    useradd -r -m -s /bin/bash -d "${APP_DIR}" "${APP_USER}"
    ok "Пользователь ${APP_USER} создан"
else
    warn "Пользователь ${APP_USER} уже существует"
fi

step "3/9 UFW Firewall"
ufw --force reset > /dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment "SSH"
ufw allow 80/tcp comment "HTTP"
ufw allow 443/tcp comment "HTTPS"
ufw --force enable > /dev/null
ok "UFW: порты 22, 80, 443 открыты"

step "4/9 Fail2ban"
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/64dao.error.log
EOF
systemctl enable fail2ban --quiet
systemctl restart fail2ban
ok "Fail2ban настроен"

step "5/9 Docker"
if ! command -v docker &>/dev/null; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) \
        signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt update -qq
    apt install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker --quiet
    usermod -aG docker "${APP_USER}"
    ok "Docker установлен"
else
    warn "Docker уже установлен"
fi

step "6/9 Node.js 20"
if ! command -v node &>/dev/null || [[ "$(node --version)" != v20* ]]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
    apt install -y -qq nodejs
fi
ok "Node.js $(node --version)"

step "7/9 Python 3.11"
if ! python3.11 --version &>/dev/null; then
    apt install -y -qq python3.11 python3.11-venv python3.11-dev python3-pip
fi
ok "Python $(python3.11 --version)"

step "8/9 Nginx + Certbot"
apt install -y -qq nginx certbot python3-certbot-nginx
systemctl enable nginx --quiet
ok "Nginx + Certbot готовы"

step "9/9 Директории"
mkdir -p "${APP_DIR}"/{backend,frontend,uploads/{reports,images}}
mkdir -p "${BACKUP_DIR}"/{db,uploads,configs}
mkdir -p /var/log/64dao /var/www/certbot
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}" "${BACKUP_DIR}"
chmod -R 755 "${APP_DIR}"
ok "Директории созданы: ${APP_DIR}"

# SSH: отключаем вход по паролю если не настроено
if [ -f /etc/ssh/sshd_config ] && ! grep -q "PermitRootLogin prohibit-password" /etc/ssh/sshd_config 2>/dev/null; then
    sed -i 's/#PermitRootLogin yes/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
    warn "SSH: вход под root теперь только по ключу"
fi

# Клонируем репозиторий если передан --repo
if [ -n "${REPO_URL}" ]; then
    step "Клонирование репозитория"
    cd "${APP_DIR}"
    if [ -d .git ]; then
        warn "Репозиторий уже существует — git pull"
        git pull
    else
        # Public репо — https без авторизации
        git clone "${REPO_URL}" .
    fi
    chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
    ok "Код загружен в ${APP_DIR}"
fi

SERVER_IP=$(curl -s --connect-timeout 3 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         ✅ Сервер подготовлен!                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo "  IP:    ${SERVER_IP}"
echo "  Код:   ${APP_DIR}"
echo ""
echo -e "${YELLOW}Следующие шаги:${NC}"
if [ -z "${REPO_URL}" ]; then
echo "  git clone https://github.com/ВАШ_ЛОГИН/64dao.git ${APP_DIR}"
fi
echo "  nano ${APP_DIR}/backend/.env"
echo "  nano ${APP_DIR}/frontend/.env.local"
echo "  bash ${APP_DIR}/deploy/scripts/deploy.sh --mode docker"
echo ""

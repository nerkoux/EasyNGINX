#!/usr/bin/env bash
# EasyNginx bootstrap installer
# Repo: https://github.com/nerkoux/EasyNGINX
# Author: Akshat Mehta <https://akshatmehta.com>
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/install.sh | sudo bash
#   sudo bash install.sh

set -euo pipefail

# ---------- Pretty output ----------------------------------------------------
if [[ -t 1 ]]; then
    C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'
    C_RED=$'\033[31m'; C_GREEN=$'\033[32m'
    C_YELLOW=$'\033[33m'; C_BLUE=$'\033[34m'; C_CYAN=$'\033[36m'
else
    C_RESET=''; C_BOLD=''; C_RED=''; C_GREEN=''; C_YELLOW=''; C_BLUE=''; C_CYAN=''
fi

log()  { printf '%s[easynginx]%s %s\n' "$C_CYAN" "$C_RESET" "$*"; }
ok()   { printf '%s[ ok ]%s %s\n'      "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf '%s[warn]%s %s\n'      "$C_YELLOW" "$C_RESET" "$*"; }
err()  { printf '%s[err ]%s %s\n'      "$C_RED" "$C_RESET" "$*" >&2; }

die() { err "$*"; exit 1; }

# ---------- Sanity checks ----------------------------------------------------
require_root() {
    if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
        die "This installer must be run as root. Try: sudo bash install.sh"
    fi
}

# ---------- Distro detection -------------------------------------------------
DISTRO_ID=""
DISTRO_FAMILY=""
PKG_MGR=""
INSTALL_CMD=""
UPDATE_CMD=""
NGINX_PKG="nginx"
CERTBOT_PKGS=""
FW_TOOL=""

detect_distro() {
    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        DISTRO_ID="${ID:-unknown}"
        local like="${ID_LIKE:-}"

        case "$DISTRO_ID" in
            ubuntu|debian|raspbian|linuxmint|pop|elementary)
                DISTRO_FAMILY="debian" ;;
            fedora)
                DISTRO_FAMILY="fedora" ;;
            rhel|centos|rocky|almalinux|ol|amzn)
                DISTRO_FAMILY="rhel" ;;
            arch|manjaro|endeavouros|cachyos)
                DISTRO_FAMILY="arch" ;;
            alpine)
                DISTRO_FAMILY="alpine" ;;
            *)
                if   [[ "$like" =~ debian ]]; then DISTRO_FAMILY="debian"
                elif [[ "$like" =~ fedora ]]; then DISTRO_FAMILY="fedora"
                elif [[ "$like" =~ rhel|centos ]]; then DISTRO_FAMILY="rhel"
                elif [[ "$like" =~ arch ]]; then DISTRO_FAMILY="arch"
                else DISTRO_FAMILY="unknown"
                fi
                ;;
        esac
    else
        die "Cannot detect distro: /etc/os-release missing."
    fi

    case "$DISTRO_FAMILY" in
        debian)
            PKG_MGR="apt-get"
            UPDATE_CMD="apt-get update -y"
            INSTALL_CMD="DEBIAN_FRONTEND=noninteractive apt-get install -y"
            CERTBOT_PKGS="certbot python3-certbot-nginx"
            FW_TOOL="ufw"
            ;;
        fedora)
            PKG_MGR="dnf"
            UPDATE_CMD="dnf -y makecache"
            INSTALL_CMD="dnf install -y"
            CERTBOT_PKGS="certbot python3-certbot-nginx"
            FW_TOOL="firewalld"
            ;;
        rhel)
            if command -v dnf >/dev/null 2>&1; then
                PKG_MGR="dnf"
                UPDATE_CMD="dnf -y makecache"
                INSTALL_CMD="dnf install -y"
            else
                PKG_MGR="yum"
                UPDATE_CMD="yum -y makecache"
                INSTALL_CMD="yum install -y"
            fi
            CERTBOT_PKGS="certbot python3-certbot-nginx"
            FW_TOOL="firewalld"
            ;;
        arch)
            PKG_MGR="pacman"
            UPDATE_CMD="pacman -Sy --noconfirm"
            INSTALL_CMD="pacman -S --noconfirm --needed"
            CERTBOT_PKGS="certbot certbot-nginx"
            FW_TOOL="ufw"
            ;;
        alpine)
            PKG_MGR="apk"
            UPDATE_CMD="apk update"
            INSTALL_CMD="apk add --no-cache"
            CERTBOT_PKGS="certbot certbot-nginx"
            FW_TOOL=""
            ;;
        *)
            die "Unsupported distro family: ${DISTRO_ID}. Open an issue at https://github.com/nerkoux/EasyNGINX/issues"
            ;;
    esac

    ok "Detected: $DISTRO_ID (family: $DISTRO_FAMILY) using $PKG_MGR"
}

# ---------- EPEL for RHEL-likes ---------------------------------------------
maybe_enable_epel() {
    if [[ "$DISTRO_FAMILY" == "rhel" ]]; then
        if ! rpm -q epel-release >/dev/null 2>&1; then
            log "Enabling EPEL repository (required for certbot on RHEL-based systems)..."
            eval "$INSTALL_CMD epel-release" || warn "Could not install epel-release; certbot install may fail."
        fi
    fi
}

# ---------- Install packages -------------------------------------------------
install_packages() {
    log "Refreshing package index..."
    eval "$UPDATE_CMD" || warn "Package index refresh reported issues; continuing."

    local base_pkgs="curl ca-certificates"
    case "$DISTRO_FAMILY" in
        debian)  base_pkgs="$base_pkgs python3 dnsutils openssl" ;;
        fedora|rhel) base_pkgs="$base_pkgs python3 bind-utils openssl" ;;
        arch)    base_pkgs="$base_pkgs python bind openssl" ;;
        alpine)  base_pkgs="$base_pkgs python3 bind-tools openssl" ;;
    esac

    log "Installing base utilities: $base_pkgs"
    eval "$INSTALL_CMD $base_pkgs"

    log "Installing nginx..."
    eval "$INSTALL_CMD $NGINX_PKG"

    log "Installing certbot ($CERTBOT_PKGS)..."
    eval "$INSTALL_CMD $CERTBOT_PKGS" || warn "Certbot install failed; SSL features will be limited."

    if [[ -n "$FW_TOOL" ]]; then
        log "Installing firewall tool: $FW_TOOL"
        eval "$INSTALL_CMD $FW_TOOL" || warn "Could not install $FW_TOOL; firewall step will be skipped."
    fi

    ok "Packages installed."
}

# ---------- Service enablement ----------------------------------------------
enable_services() {
    if command -v systemctl >/dev/null 2>&1; then
        log "Enabling and starting nginx via systemd..."
        systemctl enable nginx >/dev/null 2>&1 || true
        systemctl start  nginx || warn "nginx failed to start; check 'systemctl status nginx'."

        if [[ "$FW_TOOL" == "firewalld" ]]; then
            systemctl enable firewalld >/dev/null 2>&1 || true
            systemctl start  firewalld >/dev/null 2>&1 || true
        fi
    else
        warn "systemctl not found; skipping service enablement."
    fi
}

configure_firewall() {
    case "$FW_TOOL" in
        ufw)
            if command -v ufw >/dev/null 2>&1; then
                log "Allowing HTTP/HTTPS via ufw..."
                ufw allow 'Nginx Full' >/dev/null 2>&1 || {
                    ufw allow 80/tcp  >/dev/null 2>&1 || true
                    ufw allow 443/tcp >/dev/null 2>&1 || true
                }
                ok "ufw rules added (firewall not enabled by EasyNginx; run 'ufw enable' yourself)."
            fi
            ;;
        firewalld)
            if command -v firewall-cmd >/dev/null 2>&1; then
                log "Allowing HTTP/HTTPS via firewalld..."
                firewall-cmd --permanent --add-service=http  >/dev/null 2>&1 || true
                firewall-cmd --permanent --add-service=https >/dev/null 2>&1 || true
                firewall-cmd --reload >/dev/null 2>&1 || true
                ok "firewalld rules added."
            fi
            ;;
        *)
            warn "No supported firewall tool found; skipping firewall configuration."
            ;;
    esac
}

# ---------- Install EasyNginx files -----------------------------------------
SHARE_DIR="/usr/local/share/easynginx"
BIN_PATH="/usr/local/bin/create-host"
CONFIG_DIR="/etc/easynginx"
LOG_DIR="/var/log/easynginx"

install_easynginx_files() {
    log "Installing EasyNginx engine to $SHARE_DIR ..."

    install -d -m 0755 "$SHARE_DIR"
    install -d -m 0755 "$SHARE_DIR/lib"
    install -d -m 0755 "$SHARE_DIR/templates"
    install -d -m 0755 "$CONFIG_DIR"
    install -d -m 0755 "$CONFIG_DIR/backups"
    install -d -m 0755 "$LOG_DIR"

    local src_dir
    if [[ -n "${EASYNGINX_SRC:-}" && -d "$EASYNGINX_SRC" ]]; then
        src_dir="$EASYNGINX_SRC"
    elif [[ -d "$(dirname "$0")/lib" ]]; then
        src_dir="$(cd "$(dirname "$0")" && pwd)"
    else
        die "Cannot locate EasyNginx sources. Clone the repo and run install.sh from inside it, or set EASYNGINX_SRC."
    fi

    cp -f "$src_dir/create-host"        "$BIN_PATH"
    cp -f "$src_dir/lib/"*.py           "$SHARE_DIR/lib/"
    cp -f "$src_dir/templates/"*.conf   "$SHARE_DIR/templates/"

    chmod 0755 "$BIN_PATH"
    chmod 0644 "$SHARE_DIR/lib/"*.py
    chmod 0644 "$SHARE_DIR/templates/"*.conf

    cat > "$CONFIG_DIR/config.json" <<EOF
{
  "distro_id": "$DISTRO_ID",
  "distro_family": "$DISTRO_FAMILY",
  "package_manager": "$PKG_MGR",
  "firewall_tool": "${FW_TOOL:-none}",
  "share_dir": "$SHARE_DIR",
  "config_dir": "$CONFIG_DIR",
  "log_dir": "$LOG_DIR",
  "version": "0.1.0"
}
EOF
    chmod 0644 "$CONFIG_DIR/config.json"

    ok "EasyNginx files installed."
}

# ---------- Final verification ----------------------------------------------
verify() {
    log "Verifying installation..."
    if ! command -v nginx >/dev/null 2>&1; then
        die "nginx is not on PATH after install."
    fi
    if ! command -v create-host >/dev/null 2>&1; then
        die "create-host is not on PATH; check $BIN_PATH"
    fi
    if ! python3 -c 'import sys; sys.exit(0)' >/dev/null 2>&1; then
        die "python3 is not available."
    fi
    nginx -t >/dev/null 2>&1 || warn "nginx -t reported issues; check /etc/nginx."
    ok "Installation verified."
}

# ---------- Main -------------------------------------------------------------
main() {
    require_root
    printf '%s\n' "${C_BOLD}EasyNginx installer${C_RESET}"
    printf '%s\n' "Repo: https://github.com/nerkoux/EasyNGINX"
    printf '\n'

    detect_distro
    maybe_enable_epel
    install_packages
    enable_services
    configure_firewall
    install_easynginx_files
    verify

    printf '\n'
    ok "EasyNginx is ready."
    printf '   Run:  %ssudo create-host%s\n' "$C_BOLD" "$C_RESET"
    printf '\n'
}

main "$@"

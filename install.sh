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

print_banner() {
    # If output is being piped, skip the banner so log scrapers stay clean.
    [[ -t 1 ]] || return 0
    cat <<'BANNER'

     ______                 _   _____________   ___  __
   / ____/___ ________  __/ | / / ____/  _/ | / / |/ /
  / __/ / __ `/ ___/ / / /  |/ / / __ / //  |/ /|   / 
 / /___/ /_/ (__  ) /_/ / /|  / /_/ // // /|  //   |  
/_____/\__,_/____/\__, /_/ |_/\____/___/_/ |_//_/|_|  
                 /____/                                            

BANNER
    printf '  %sFriendly nginx setup for everyone.%s\n' "$C_BOLD" "$C_RESET"
    printf '  %shttps://github.com/nerkoux/EasyNGINX%s\n\n' "$C_CYAN" "$C_RESET"
}

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

# ---------- EasyNginx files ---------------------------------------------
SHARE_DIR="/usr/local/share/easynginx"
EZ_BIN_PATH="/usr/local/bin/easynginx"
CONFIG_DIR="/etc/easynginx"
LOG_DIR="/var/log/easynginx"

# Modes: "fresh" (default) or "restore". Set by ask_install_mode().
INSTALL_MODE="fresh"
RESTORE_ARCHIVE=""

ask_install_mode() {
    if [[ -n "${EASYNGINX_RESTORE:-}" ]]; then
        INSTALL_MODE="restore"
        RESTORE_ARCHIVE="$EASYNGINX_RESTORE"
        log "Non-interactive restore requested: $RESTORE_ARCHIVE"
        return
    fi

    if [[ "${EASYNGINX_FRESH:-0}" == "1" ]]; then
        INSTALL_MODE="fresh"
        return
    fi

    if [[ ! -t 0 ]]; then
        # Piped install — default to fresh unless EASYNGINX_RESTORE was given.
        INSTALL_MODE="fresh"
        return
    fi

    printf '\n%sChoose install mode:%s\n' "$C_BOLD" "$C_RESET"
    printf '  1) Fresh install (default)\n'
    printf '  2) Restore from a previous EasyNginx backup\n'
    local choice
    read -r -p "  Select [1-2]: " choice || choice=""
    case "${choice:-1}" in
        2) INSTALL_MODE="restore" ;;
        *) INSTALL_MODE="fresh"   ;;
    esac
}

pick_restore_archive() {
    # Use the bootstrap helper from the source tree to enumerate candidates.
    local src_dir
    if [[ -n "${EASYNGINX_SRC:-}" && -d "$EASYNGINX_SRC" ]]; then
        src_dir="$EASYNGINX_SRC"
    elif [[ -d "$(dirname "$0")/lib" ]]; then
        src_dir="$(cd "$(dirname "$0")" && pwd)"
    else
        die "Cannot locate EasyNginx sources for restore step."
    fi

    if [[ -n "$RESTORE_ARCHIVE" ]]; then
        if [[ ! -f "$RESTORE_ARCHIVE" ]]; then
            die "Backup file does not exist: $RESTORE_ARCHIVE"
        fi
        return
    fi

    log "Searching for backups in common locations..."
    mapfile -t candidates < <(python3 "$src_dir/lib/bootstrap_restore.py" find | awk -F'\t' '{print $2}')

    if [[ ${#candidates[@]} -eq 0 ]]; then
        warn "No backups found automatically."
        local manual=""
        while [[ -z "$manual" || ! -f "$manual" ]]; do
            read -r -p "  Path to backup .tar.gz: " manual || manual=""
            if [[ -z "$manual" ]]; then
                die "Restore cancelled."
            fi
            if [[ ! -f "$manual" ]]; then
                warn "File does not exist: $manual"
                manual=""
            fi
        done
        RESTORE_ARCHIVE="$manual"
        return
    fi

    printf '\n%sAvailable backups:%s\n' "$C_BOLD" "$C_RESET"
    python3 "$src_dir/lib/bootstrap_restore.py" find \
        | awk -F'\t' '{printf "  %s) %s\n     %s  host: %s  label: %s\n", $1, $2, $3, $4, $5}'
    printf '  %d) Provide a custom path\n' "$(( ${#candidates[@]} + 1 ))"

    local pick=""
    while :; do
        read -r -p "  Choose [1-$(( ${#candidates[@]} + 1 ))]: " pick || pick=""
        if [[ "$pick" =~ ^[0-9]+$ ]]; then
            if (( pick >= 1 && pick <= ${#candidates[@]} )); then
                RESTORE_ARCHIVE="${candidates[$((pick - 1))]}"
                return
            fi
            if (( pick == ${#candidates[@]} + 1 )); then
                local manual=""
                while [[ -z "$manual" || ! -f "$manual" ]]; do
                    read -r -p "  Path to backup .tar.gz: " manual || manual=""
                    if [[ -z "$manual" ]]; then
                        die "Restore cancelled."
                    fi
                    [[ -f "$manual" ]] || warn "File does not exist: $manual"
                done
                RESTORE_ARCHIVE="$manual"
                return
            fi
        fi
        warn "Invalid selection."
    done
}

run_restore() {
    local src_dir
    if [[ -n "${EASYNGINX_SRC:-}" && -d "$EASYNGINX_SRC" ]]; then
        src_dir="$EASYNGINX_SRC"
    else
        src_dir="$(cd "$(dirname "$0")" && pwd)"
    fi

    log "Inspecting backup: $RESTORE_ARCHIVE"
    if ! python3 "$src_dir/lib/bootstrap_restore.py" inspect "$RESTORE_ARCHIVE" >/tmp/easynginx-manifest.json 2>/dev/null; then
        die "Backup is unreadable or not an EasyNginx archive."
    fi

    install -d -m 0755 "$CONFIG_DIR/backups/snapshots"

    log "Restoring backup (a safety snapshot will be saved first)..."
    if ! python3 "$src_dir/lib/bootstrap_restore.py" restore "$RESTORE_ARCHIVE"; then
        die "Restore failed. Re-run install.sh and choose 'Fresh install', or fix the archive and try again."
    fi
    ok "Restore complete."

    log "Validating nginx config from restored files..."
    if nginx -t >/tmp/easynginx-nginx-t.log 2>&1; then
        ok "nginx -t passed."
        if command -v systemctl >/dev/null 2>&1; then
            systemctl reload nginx >/dev/null 2>&1 \
                || systemctl restart nginx >/dev/null 2>&1 \
                || warn "nginx reload failed; check 'systemctl status nginx'."
        fi
    else
        warn "nginx -t failed after restore. Inspect /tmp/easynginx-nginx-t.log."
        warn "Your pre-restore snapshot is at $CONFIG_DIR/backups/snapshots/"
    fi
}

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

    cp -f "$src_dir/easynginx"          "$EZ_BIN_PATH"
    cp -f "$src_dir/lib/"*.py           "$SHARE_DIR/lib/"
    cp -f "$src_dir/templates/"*.conf   "$SHARE_DIR/templates/"
    if compgen -G "$src_dir/templates/html_vendors/*.html" > /dev/null; then
        install -d -m 0755 "$SHARE_DIR/templates/html_vendors"
        cp -f "$src_dir/templates/html_vendors/"*.html \
              "$SHARE_DIR/templates/html_vendors/"
    fi

    chmod 0755 "$EZ_BIN_PATH"
    chmod 0644 "$SHARE_DIR/lib/"*.py
    chmod 0644 "$SHARE_DIR/templates/"*.conf 2>/dev/null || true
    chmod 0644 "$SHARE_DIR/templates/html_vendors/"*.html 2>/dev/null || true

    # Older installs may have left a create-host binary behind. Remove it
    # so the user doesn't get confused about which CLI is the real one.
    rm -f /usr/local/bin/create-host

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
    if ! command -v easynginx >/dev/null 2>&1; then
        die "easynginx is not on PATH; check $EZ_BIN_PATH"
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
    print_banner
    printf '%s\n' "${C_BOLD}EasyNginx installer${C_RESET}"
    printf '%s\n' "Repo: https://github.com/nerkoux/EasyNGINX"
    printf '\n'

    detect_distro
    ask_install_mode
    maybe_enable_epel
    install_packages
    enable_services
    configure_firewall
    install_easynginx_files

    if [[ "$INSTALL_MODE" == "restore" ]]; then
        pick_restore_archive
        run_restore
    fi

    verify

    printf '\n'
    if [[ "$INSTALL_MODE" == "restore" ]]; then
        ok "EasyNginx is ready and your sites are restored."
    else
        ok "EasyNginx is ready."
    fi
    printf '   Run:  %ssudo easynginx create%s\n'          "$C_BOLD" "$C_RESET"
    printf '         %ssudo easynginx list%s   • status • doctor\n' "$C_BOLD" "$C_RESET"
    printf '   Backup:  %ssudo easynginx backup%s\n'        "$C_BOLD" "$C_RESET"
    printf '\n'
}

main "$@"

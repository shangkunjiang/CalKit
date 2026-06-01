#!/usr/bin/env bash
# ============================================================
# CalKit v0.4.0 — One-click Installer for Ubuntu / Debian
# ============================================================
# Usage:
#   1. Unpack:  tar -xzf CalKit_v0.4.0_Ubuntu.tar.gz
#   2. Install: cd CalKit_v0.4.0_Ubuntu && ./install_calkit.sh
#
# Options:
#   --venv         Create an isolated virtual environment (recommended)
#   --user         pip install --user (no sudo needed)
#   --system       pip install system-wide (may need sudo)
#   --help         Show this help
# ============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_MODE="venv"   # venv | user | system

# ── Banner ───────────────────────────────────────────────────

echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════╗"
echo "║        CalKit v0.4.0 — Ubuntu Installer       ║"
echo "║   Multi-scale Computation Analysis Toolkit    ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Parse arguments ──────────────────────────────────────────

for arg in "$@"; do
    case "$arg" in
        --venv)   INSTALL_MODE="venv"   ;;
        --user)   INSTALL_MODE="user"   ;;
        --system) INSTALL_MODE="system" ;;
        --help|-h)
            echo "Usage: ./install_calkit.sh [--venv|--user|--system]"
            echo ""
            echo "  --venv    Create isolated virtual environment (default, recommended)"
            echo "  --user    pip install --user (no root required)"
            echo "  --system  pip install system-wide (may need sudo)"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            exit 1
            ;;
    esac
done

# ── Step 1: Detect Python ────────────────────────────────────

echo -e "${YELLOW}[1/6] Detecting Python 3.8+ ...${NC}"

PYTHON=""
for py in python3.12 python3.11 python3.10 python3.9 python3.8 python3; do
    if command -v "$py" &>/dev/null; then
        VER=$("$py" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 8 ]; then
            PYTHON="$py"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${RED}Error: Python 3.8+ not found.${NC}"
    echo ""
    echo "  Install Python 3 on Ubuntu/Debian:"
    echo "    sudo apt update"
    echo "    sudo apt install python3 python3-pip python3-venv"
    exit 1
fi
echo -e "  Found: ${GREEN}$($PYTHON --version)${NC}"

# ── Step 2: Install pip if missing ───────────────────────────

echo -e "${YELLOW}[2/6] Ensuring pip is available ...${NC}"
if ! "$PYTHON" -m pip --version &>/dev/null; then
    echo -e "  Installing pip..."
    "$PYTHON" -m ensurepip --upgrade 2>/dev/null || {
        curl -sS https://bootstrap.pypa.io/get-pip.py | "$PYTHON"
    }
fi
echo -e "  pip: ${GREEN}$("$PYTHON" -m pip --version | cut -d' ' -f1,2)${NC}"

# ── Step 3: Install CalKit ───────────────────────────────────

echo -e "${YELLOW}[3/6] Installing CalKit ...${NC}"

case "$INSTALL_MODE" in
    venv)
        CALKIT_DIR="$HOME/.calkit"
        VENV_DIR="$CALKIT_DIR/venv"

        if [ ! -d "$CALKIT_DIR" ]; then
            mkdir -p "$CALKIT_DIR"
        fi

        if [ ! -d "$VENV_DIR" ]; then
            echo -e "  Creating virtual environment at ${CYAN}$VENV_DIR${NC} ..."
            "$PYTHON" -m venv "$VENV_DIR"
        else
            echo -e "  Using existing virtual environment at ${CYAN}$VENV_DIR${NC}"
        fi

        VENV_PYTHON="$VENV_DIR/bin/python"
        "$VENV_PYTHON" -m pip install --quiet --upgrade pip
        "$VENV_PYTHON" -m pip install --quiet -e "$SCRIPT_DIR"
        echo -e "  CalKit installed: ${GREEN}$("$VENV_PYTHON" -c "import ckit; print(ckit.__version__)")${NC}"
        ;;
    user)
        "$PYTHON" -m pip install --user --quiet -e "$SCRIPT_DIR"
        echo -e "  CalKit installed: ${GREEN}$("$PYTHON" -c "import ckit; print(ckit.__version__)")${NC}"
        ;;
    system)
        echo -e "  Installing system-wide..."
        "$PYTHON" -m pip install --quiet -e "$SCRIPT_DIR" 2>/dev/null || {
            echo -e "  ${YELLOW}Permission denied, trying with sudo...${NC}"
            sudo "$PYTHON" -m pip install --quiet -e "$SCRIPT_DIR"
        }
        echo -e "  CalKit installed: ${GREEN}$("$PYTHON" -c "import ckit; print(ckit.__version__)")${NC}"
        ;;
esac

# ── Step 4: Create calkit wrapper ────────────────────────────

echo -e "${YELLOW}[4/6] Creating calkit launcher ...${NC}"

if [ "$INSTALL_MODE" = "venv" ]; then
    WRAPPER="$CALKIT_DIR/calkit"
    cat > "$WRAPPER" << 'WRAPPEREOF'
#!/usr/bin/env bash
exec "$HOME/.calkit/venv/bin/python" -m ckit.cli "$@"
WRAPPEREOF
    chmod +x "$WRAPPER"
    echo -e "  Launcher: ${GREEN}$WRAPPER${NC}"
else
    # For user/system installs, calkit is installed as a console script by pip
    WRAPPER=""
    echo -e "  Using pip-installed console script: ${GREEN}calkit${NC}"
fi

# ── Step 5: Add to PATH ──────────────────────────────────────

echo -e "${YELLOW}[5/6] Configuring PATH ...${NC}"

add_to_path() {
    local SHELL_RC="$1"

    if [ -f "$SHELL_RC" ]; then
        if grep -q "calkit" "$SHELL_RC" 2>/dev/null; then
            echo -e "  Already in: ${GREEN}$SHELL_RC${NC}"
            return
        fi

        echo "" >> "$SHELL_RC"
        echo "# CalKit (added by install_calkit.sh)" >> "$SHELL_RC"

        if [ "$INSTALL_MODE" = "venv" ]; then
            echo "export PATH=\"\$HOME/.calkit:\$PATH\"" >> "$SHELL_RC"
        fi
        echo -e "  Added to: ${GREEN}$SHELL_RC${NC}"
    fi
}

add_to_path "$HOME/.bashrc"
[ -f "$HOME/.zshrc" ] && add_to_path "$HOME/.zshrc"
if ! grep -q "calkit" "$HOME/.bashrc" 2>/dev/null && ! grep -q "calkit" "$HOME/.zshrc" 2>/dev/null; then
    add_to_path "$HOME/.profile"
fi

# ── Step 6: Initialize config ────────────────────────────────

echo -e "${YELLOW}[6/6] Initializing configuration ...${NC}"

CONFIG_DIR="${CALKIT_DIR:-$HOME/.calkit}"
CONFIG_FILE="$CONFIG_DIR/config.json"

if [ ! -d "$CONFIG_DIR" ]; then
    mkdir -p "$CONFIG_DIR"
fi

if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" << 'EOF'
{
    "_comment": "CalKit Configuration. Edit directly or use: calkit config",
    "paths": {
        "pseudopotential_dir": "",
        "bader_executable": "bader",
        "vaspkit_executable": "vaspkit",
        "default_output_dir": ""
    },
    "defaults": {
        "temperature": 298.15,
        "dpi": 150,
        "output_format": "excel",
        "pdos_pattern": "PDOS*.dat"
    },
    "ui": {
        "color_output": true,
        "show_banner": true
    }
}
EOF
    echo -e "  Config created: ${GREEN}$CONFIG_FILE${NC}"
else
    echo -e "  Config exists: ${GREEN}$CONFIG_FILE${NC}"
fi

# ── Done ─────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}${BOLD}============================================${NC}"
echo -e "${GREEN}${BOLD}   CalKit v0.4.0 — Installation Complete!${NC}"
echo -e "${GREEN}${BOLD}============================================${NC}"
echo ""

if [ "$INSTALL_MODE" = "venv" ]; then
    echo -e "  Venv:       ${CYAN}$VENV_DIR${NC}"
    echo -e "  Launcher:   ${CYAN}$CALKIT_DIR/calkit${NC}"
fi
echo -e "  Config:     ${CYAN}$CONFIG_FILE${NC}"
echo ""
echo -e "  ${YELLOW}To activate in current shell:${NC}"
if [ "$INSTALL_MODE" = "venv" ]; then
    echo -e "    ${CYAN}export PATH=\"\$HOME/.calkit:\$PATH\"${NC}"
    echo -e "    or start a new terminal and run:  ${CYAN}calkit${NC}"
else
    echo -e "    ${CYAN}calkit${NC}"
fi
echo ""
echo -e "  ${YELLOW}Quick start:${NC}"
echo -e "    ${CYAN}calkit${NC}              # Launch interactive menu"
echo -e "    ${CYAN}calkit force -d .${NC}   # Force convergence analysis"
echo -e "    ${CYAN}calkit bader -d .${NC}   # Bader charge analysis"
echo -e "    ${CYAN}calkit config${NC}        # Edit configuration"
echo ""

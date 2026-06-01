#!/usr/bin/env bash
# ============================================================
# CalKit — One-click deployment for Linux
# Supports: Ubuntu 18.04+, CentOS 7+, RHEL 7+, Debian 10+
# ============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

CALKIT_DIR="$HOME/.calkit"
CONFIG_FILE="$CALKIT_DIR/config.json"
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}   CalKit — Installation Script${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ---- Step 1: Detect Python ----
echo -e "${YELLOW}[1/5] Detecting Python 3.8+ ...${NC}"

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
    echo -e "${RED}Error: Python 3.8+ not found. Please install it first.${NC}"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  CentOS/RHEL:   sudo yum install python38 python38-pip"
    exit 1
fi
echo -e "  Found: ${GREEN}$PYTHON ($($PYTHON --version))${NC}"

# ---- Step 2: Create virtual environment ----
echo -e "${YELLOW}[2/5] Creating virtual environment at $CALKIT_DIR/venv ...${NC}"

if [ ! -d "$CALKIT_DIR" ]; then
    mkdir -p "$CALKIT_DIR"
fi

# -- On older systems without ensurepip, try pip install first --
if [ ! -d "$CALKIT_DIR/venv" ]; then
    $PYTHON -m venv "$CALKIT_DIR/venv" 2>/dev/null || {
        echo -e "${YELLOW}  venv module failed, trying --without-pip then bootstrapping...${NC}"
        $PYTHON -m venv --without-pip "$CALKIT_DIR/venv"
        curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
        "$CALKIT_DIR/venv/bin/python" /tmp/get-pip.py --quiet
        rm -f /tmp/get-pip.py
    }
fi

VENV_PYTHON="$CALKIT_DIR/venv/bin/python"
VENV_PIP="$CALKIT_DIR/venv/bin/pip"

echo -e "  Virtual env: ${GREEN}$CALKIT_DIR/venv${NC}"

# ---- Step 3: Install CalKit ----
echo -e "${YELLOW}[3/5] Installing CalKit and dependencies ...${NC}"

"$VENV_PIP" install --quiet --upgrade pip
"$VENV_PIP" install --quiet -e "$INSTALL_DIR"

echo -e "  Package installed: ${GREEN}$("$VENV_PYTHON" -c "import ckit; print(ckit.__version__)")${NC}"

# ---- Step 4: Create wrapper script ----
echo -e "${YELLOW}[4/5] Creating executable wrapper ...${NC}"

WRAPPER="$CALKIT_DIR/calkit"
cat > "$WRAPPER" << EOF
#!/usr/bin/env bash
exec "$CALKIT_DIR/venv/bin/python" -m ckit.cli "\$@"
EOF
chmod +x "$WRAPPER"

# ---- Step 4b: Add to PATH ----
add_to_path() {
    local SHELL_RC=""
    case "$SHELL" in
        */zsh)  SHELL_RC="$HOME/.zshrc"  ;;
        */bash) SHELL_RC="$HOME/.bashrc" ;;
        *)      SHELL_RC="$HOME/.profile" ;;
    esac

    if [ -f "$SHELL_RC" ]; then
        if ! grep -q "calkit" "$SHELL_RC" 2>/dev/null; then
            echo "" >> "$SHELL_RC"
            echo "# CalKit (added by setup.sh)" >> "$SHELL_RC"
            echo "export PATH=\"$CALKIT_DIR:\$PATH\"" >> "$SHELL_RC"
            echo -e "  Added to: ${GREEN}$SHELL_RC${NC}"
        else
            echo -e "  Already in: ${GREEN}$SHELL_RC${NC}"
        fi
    fi
}
add_to_path

# ---- Step 5: Initialize config ----
echo -e "${YELLOW}[5/5] Initializing configuration ...${NC}"

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

# ---- Done ----
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   CalKit installed successfully!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "  Executable: ${CYAN}$CALKIT_DIR/calkit${NC}"
echo -e "  Config:     ${CYAN}$CONFIG_FILE${NC}"
echo -e "  Venv:       ${CYAN}$CALKIT_DIR/venv${NC}"
echo ""
echo -e "  ${YELLOW}To use immediately, run:${NC}"
echo -e "    ${CYAN}source ~/.bashrc${NC}   (or ~/.zshrc / ~/.profile)"
echo ""
echo -e "  ${YELLOW}Launch interactive mode:${NC}"
echo -e "    ${CYAN}calkit${NC}"
echo ""
echo -e "  ${YELLOW}Or use CLI shortcuts:${NC}"
echo -e "    ${CYAN}calkit force -o OUTCAR -i INCAR${NC}"
echo -e "    ${CYAN}calkit bader -d ./vasp_run${NC}"
echo -e "    ${CYAN}calkit config${NC}"
echo ""

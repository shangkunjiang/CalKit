#!/usr/bin/env bash
# ============================================================
# CalKit v0.4.0 — Packaging Script for Ubuntu
# ============================================================
# Usage (run on Windows with Git Bash / WSL, or on Linux):
#   bash package_calkit.sh
#
# Output:
#   CalKit_v0.4.0_Ubuntu.tar.gz
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_NAME="CalKit_v0.4.0_Ubuntu"
TMP_DIR="$SCRIPT_DIR/_pkg_tmp"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}   CalKit v0.4.0 — Packaging Script${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ── Step 1: Clean previous build ─────────────────────────────

echo -e "${YELLOW}[1/4] Cleaning previous build artifacts ...${NC}"

rm -rf "$TMP_DIR"
rm -f "$SCRIPT_DIR/${OUTPUT_NAME}.tar.gz"
rm -f "$SCRIPT_DIR/${OUTPUT_NAME}.tar"
mkdir -p "$TMP_DIR"

echo -e "  Done.${NC}"

# ── Step 2: Copy project files ──────────────────────────────

echo -e "${YELLOW}[2/4] Copying project files ...${NC}"

PKG_DIR="$TMP_DIR/$OUTPUT_NAME"
mkdir -p "$PKG_DIR/ckit"

# Copy ckit/ package (all .py files)
cp "$SCRIPT_DIR/ckit/"*.py "$PKG_DIR/ckit/" 2>/dev/null || true

# Copy project config files
cp "$SCRIPT_DIR/pyproject.toml"   "$PKG_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/requirements.txt"  "$PKG_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/README.md"        "$PKG_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/setup.sh"         "$PKG_DIR/" 2>/dev/null || true

# Copy install script (this script itself)
cp "$SCRIPT_DIR/install_calkit.sh" "$PKG_DIR/" 2>/dev/null || true

# Copy this packaging script for reference
cp "$SCRIPT_DIR/package_calkit.sh" "$PKG_DIR/" 2>/dev/null || true

# Set permissions
chmod 644 "$PKG_DIR/ckit/"*.py
chmod 644 "$PKG_DIR/"*.toml "$PKG_DIR/"*.txt "$PKG_DIR/"*.md "$PKG_DIR/"*.sh
chmod 755 "$PKG_DIR/install_calkit.sh"
chmod 755 "$PKG_DIR/setup.sh" 2>/dev/null || true
chmod 755 "$PKG_DIR/package_calkit.sh" 2>/dev/null || true

echo -e "  Copied: ${GREEN}ckit/ + project files${NC}"

# ── Step 3: Create tar.gz ───────────────────────────────────

echo -e "${YELLOW}[3/4] Creating tar.gz archive ...${NC}"

cd "$TMP_DIR"
tar -czf "$SCRIPT_DIR/${OUTPUT_NAME}.tar.gz" "$OUTPUT_NAME/"

cd "$SCRIPT_DIR"
PKG_SIZE=$(du -h "${OUTPUT_NAME}.tar.gz" | cut -f1)
echo -e "  Archive: ${GREEN}${OUTPUT_NAME}.tar.gz ($PKG_SIZE)${NC}"

# ── Step 4: Verify archive ───────────────────────────────────

echo -e "${YELLOW}[4/4] Verifying archive contents ...${NC}"

TMP_VERIFY="$TMP_DIR/_verify"
rm -rf "$TMP_VERIFY"
mkdir -p "$TMP_VERIFY"
cd "$TMP_VERIFY"
tar -xzf "$SCRIPT_DIR/${OUTPUT_NAME}.tar.gz"

FILE_COUNT=$(find "$TMP_VERIFY/$OUTPUT_NAME" -type f | wc -l)
echo -e "  Files in archive: ${GREEN}$FILE_COUNT${NC}"

# List key files
echo -e "  ${CYAN}Archive structure:${NC}"
find "$TMP_VERIFY/$OUTPUT_NAME" -type f | sort | sed "s|$TMP_VERIFY/$OUTPUT_NAME/|    |"

# Cleanup
cd "$SCRIPT_DIR"
rm -rf "$TMP_DIR"

# ── Done ─────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   Packaging Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "  Archive:   ${CYAN}${OUTPUT_NAME}.tar.gz${NC}"
echo -e "  Size:      ${CYAN}$PKG_SIZE${NC}"
echo -e "  Location:  ${CYAN}$SCRIPT_DIR${NC}"
echo ""
echo -e "  ${YELLOW}To install on Ubuntu:${NC}"
echo -e "    ${CYAN}scp ${OUTPUT_NAME}.tar.gz user@ubuntu:/path/${NC}"
echo -e "    ${CYAN}ssh user@ubuntu${NC}"
echo -e "    ${CYAN}cd /path && tar -xzf ${OUTPUT_NAME}.tar.gz${NC}"
echo -e "    ${CYAN}cd ${OUTPUT_NAME} && bash install_calkit.sh${NC}"
echo ""

#!/bin/bash
# Car-HACK Dashboard - Automated Setup Script
# This script installs dependencies and sets up the virtual CAN interface

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         Car-HACK Dashboard - Setup Script                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${YELLOW}⚠️  Warning: This script is designed for Linux systems${NC}"
    echo "   For WSL2, you can still run it but vcan may not work"
    read -p "   Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Python version
echo -e "${BLUE}[1/6]${NC} Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | grep -oP '\d+\.\d+' | head -1)
    REQUIRED_VERSION="3.7"
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
        echo -e "      ${GREEN}✓${NC} Python $PYTHON_VERSION found"
    else
        echo -e "      ${RED}✗${NC} Python $PYTHON_VERSION is too old (need 3.7+)"
        exit 1
    fi
else
    echo -e "      ${RED}✗${NC} Python 3 not found"
    echo "      Install with: sudo apt install python3"
    exit 1
fi

# Install Python dependencies
echo -e "${BLUE}[2/6]${NC} Installing Python dependencies..."
if pip3 install -r requirements.txt --quiet; then
    echo -e "      ${GREEN}✓${NC} Python packages installed"
else
    echo -e "      ${RED}✗${NC} Failed to install Python packages"
    echo "      Try manually: pip3 install python-can"
    exit 1
fi

# Install system dependencies
echo -e "${BLUE}[3/6]${NC} Installing system dependencies..."
if command -v apt &> /dev/null; then
    sudo apt update -qq
    if sudo apt install -y can-utils python3-tk -qq; then
        echo -e "      ${GREEN}✓${NC} System packages installed (apt)"
    else
        echo -e "      ${YELLOW}⚠${NC}  Some packages may have failed"
    fi
elif command -v dnf &> /dev/null; then
    if sudo dnf install -y can-utils python3-tkinter -q; then
        echo -e "      ${GREEN}✓${NC} System packages installed (dnf)"
    else
        echo -e "      ${YELLOW}⚠${NC}  Some packages may have failed"
    fi
elif command -v pacman &> /dev/null; then
    if sudo pacman -S --noconfirm can-utils tk; then
        echo -e "      ${GREEN}✓${NC} System packages installed (pacman)"
    else
        echo -e "      ${YELLOW}⚠${NC}  Some packages may have failed"
    fi
else
    echo -e "      ${YELLOW}⚠${NC}  Unknown package manager, skipping system packages"
    echo "      Please install manually: can-utils, python3-tk"
fi

# Setup vcan0
echo -e "${BLUE}[4/6]${NC} Setting up virtual CAN interface (vcan0)..."
if sudo modprobe vcan 2>/dev/null; then
    if ! ip link show vcan0 &> /dev/null; then
        sudo ip link add dev vcan0 type vcan
        sudo ip link set up vcan0
    fi
    
    if ip link show vcan0 &> /dev/null; then
        echo -e "      ${GREEN}✓${NC} vcan0 interface ready"
    else
        echo -e "      ${RED}✗${NC} Failed to create vcan0"
    fi
else
    echo -e "      ${YELLOW}⚠${NC}  vcan module not available (WSL2?)"
    echo "      Dashboard will work with keyboard controls only"
fi

# Make vcan0 persistent (optional)
echo -e "${BLUE}[5/6]${NC} Make vcan0 persistent on boot? (optional)"
read -p "      Create systemd service? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cat << 'EOF' | sudo tee /etc/systemd/system/vcan.service > /dev/null
[Unit]
Description=Virtual CAN Interface
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/sbin/modprobe vcan
ExecStart=/sbin/ip link add dev vcan0 type vcan
ExecStart=/sbin/ip link set up vcan0

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl enable vcan.service
    sudo systemctl start vcan.service
    echo -e "      ${GREEN}✓${NC} vcan0 will start automatically on boot"
fi

# Test installation
echo -e "${BLUE}[6/6]${NC} Testing installation..."

# Test Python imports
if python3 -c "import can; import tkinter" 2>/dev/null; then
    echo -e "      ${GREEN}✓${NC} Python modules working"
else
    echo -e "      ${RED}✗${NC} Python module test failed"
    exit 1
fi

# Test CAN interface
if ip link show vcan0 &> /dev/null; then
    if cansend vcan0 123#DEADBEEF 2>/dev/null; then
        echo -e "      ${GREEN}✓${NC} CAN interface working"
        CAN_WORKS=true
    else
        echo -e "      ${YELLOW}⚠${NC}  CAN interface exists but cansend failed"
        CAN_WORKS=false
    fi
else
    echo -e "      ${YELLOW}⚠${NC}  CAN interface not available (keyboard mode only)"
    CAN_WORKS=false
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  Setup Complete! 🎉                       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$CAN_WORKS" = true ]; then
    echo -e "${GREEN}✓ Full installation successful!${NC}"
    echo ""
    echo "Available control methods:"
    echo "  1. Keyboard controls (E, ↑, ↓, G, ←, →)"
    echo "  2. CAN commands (cansend vcan0 100#64)"
    echo ""
    echo "Quick start:"
    echo "  ${BLUE}Terminal 1:${NC} python3 main-dash.py"
    echo "  ${BLUE}Terminal 2:${NC} candump vcan0"
    echo "  ${BLUE}Terminal 3:${NC} cansend vcan0 100#64"
else
    echo -e "${YELLOW}⚠ Partial installation (keyboard controls only)${NC}"
    echo ""
    echo "Available control methods:"
    echo "  1. Keyboard controls (E, ↑, ↓, G, ←, →)"
    echo ""
    echo "Quick start:"
    echo "  ${BLUE}python3 main-dash.py${NC}"
    echo "  Click the window, press E to start engine"
fi

echo ""
echo "Documentation:"
echo "  📖 README.md - Full project documentation"
echo "  📋 CAN_ID_MAP.md - CAN protocol reference"
echo "  ⌨️  KEYBOARD_CONTROLS.txt - Keyboard shortcuts"
echo ""
echo -e "${BLUE}Start the dashboard now with:${NC} python3 main-dash.py"
echo ""


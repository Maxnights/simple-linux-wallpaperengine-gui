#!/bin/bash

# Function to detect the OS and install system dependencies
install_system_deps() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        echo "Cannot detect OS. Please install Python 3 and venv manually."
        exit 1
    fi

    echo "Detected OS: $OS"
    
    case $OS in
        ubuntu|debian|pop|linuxmint|kali)
            echo "Installing dependencies for Debian/Ubuntu based systems..."
            sudo apt update
            sudo apt install -y python3 python3-venv python3-pip git
            ;;
        fedora|rhel|centos)
            echo "Installing dependencies for Fedora based systems..."
            sudo dnf install -y python3 python3-pip git
            ;;
        arch|manjaro|endeavouros)
            echo "Installing dependencies for Arch based systems..."
            sudo pacman -Sy --noconfirm python python-pip git
            ;;
        *)
            echo "Unsupported or unknown distribution: $OS"
            echo "Please ensure Python 3, pip, and venv are installed."
            read -p "Press Enter to continue or Ctrl+C to abort..."
            ;;
    esac
}

echo "---------------------------------------"
echo " Simple Linux WallpaperEngine GUI Setup"
echo "---------------------------------------"

# 1. Install System Dependencies
install_system_deps

# 2. Check for linux-wallpaperengine backend
if ! command -v linux-wallpaperengine &> /dev/null; then
    echo "Warning: 'linux-wallpaperengine' backend not found in PATH."
    echo "This GUI requires the backend to function."
    echo "Please check the README.md for installation instructions."
    sleep 2
fi

# 3. Setup Python Environment
echo "Setting up Python virtual environment..."

if [ -d ".venv" ]; then
    rm -rf .venv
fi

python3 -m venv .venv
if [ $? -ne 0 ]; then
    echo "Error creating virtual environment."
    exit 1
fi

source .venv/bin/activate

# 4. Install Python Requirements
echo "Installing Python libraries..."
pip install --upgrade pip
pip install -r requirements.txt

chmod +x run_gui.sh

echo "---------------------------------------"
echo "Installation Complete!"
echo "Run the app using: ./run_gui.sh"
echo "---------------------------------------"

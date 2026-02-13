#!/bin/bash

# Setup script for Utah Unreachability Mapping Tool
# This script will set up the virtual environment and install dependencies

echo "=========================================="
echo "Utah Unreachability Mapping Tool - Setup"
echo "=========================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.11 or higher"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to create virtual environment"
    exit 1
fi

echo "✓ Virtual environment created"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to activate virtual environment"
    exit 1
fi

echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies (this may take a few minutes)..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Error: Failed to install dependencies"
    echo "Please check the error messages above"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "To get started:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Show project info:"
echo "   python3 -m src.cli info"
echo ""
echo "3. Run the complete pipeline:"
echo "   python3 -m src.cli run_all"
echo ""
echo "4. Or run individual steps:"
echo "   python3 -m src.cli fetch_data"
echo "   python3 -m src.cli preprocess"
echo "   python3 -m src.cli compute_distance"
echo "   python3 -m src.cli find_unreachable"
echo "   python3 -m src.cli visualize"
echo ""
echo "For more information, see:"
echo "  - QUICKSTART.md"
echo "  - README.md"
echo "  - PROJECT_STATUS.md"
echo ""
echo "Happy mapping! 🗺️"

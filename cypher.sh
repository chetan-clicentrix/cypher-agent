#!/bin/bash
# Cypher AI Assistant - Quick Start Script (Linux/Mac)

echo ""
echo "========================================"
echo "  Cypher AI Assistant"
echo "========================================"
echo ""

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "[*] Activating virtual environment..."
    source venv/bin/activate
    echo "[+] Virtual environment activated!"
    echo ""
else
    echo "[!] Virtual environment not found!"
    echo "[!] Please run: python -m venv venv"
    exit 1
fi

# Run Cypher
echo "[*] Starting Cypher..."
echo ""
python -m src.core.engine

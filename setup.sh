#!/bin/bash

# Quick Start Script for MarketMind AI

echo "==========================================="
echo "  MarketMind AI - Quick Start Setup"
echo "==========================================="
echo ""

# Check Python version
echo "🔍 Checking Python version..."
python3 --version

# Create virtual environment
echo ""
echo "🔧 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo ""
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright Chromium for NSE Akamai bypass
echo ""
echo "🎭 Installing Playwright Chromium (NSE data bypass)..."
playwright install chromium

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p logs data

echo ""
echo "==========================================="
echo "  ✅ Setup Complete!"
echo "==========================================="
echo ""
echo "To run MarketMind AI:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run the application: python main.py"
echo ""
echo "To customize stocks, edit: config/config.yaml"
echo ""

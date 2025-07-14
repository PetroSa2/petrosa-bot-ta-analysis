#!/bin/bash

# Petrosa TA Bot Development Setup Script

set -e

echo "🚀 Setting up Petrosa TA Bot development environment..."

# Check Python version
echo "📋 Checking Python version..."
python3 --version

# Create virtual environment
echo "🔧 Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
echo "🔗 Installing pre-commit hooks..."
pip install pre-commit
pre-commit install

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "✅ Created .env file. Please update with your configuration."
fi

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x scripts/*.sh

echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env with your configuration"
echo "2. Run 'make test' to verify setup"
echo "3. Run 'make run' to start the TA Bot locally" 
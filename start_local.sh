#!/bin/bash
# ============================================================================
# Qwen Chat CLI Startup Script
# Interactive command-line interface for Qwen AI models.
#
# Usage:
#   ./start_local.sh                        # Use default model
#   ./start_local.sh --help                 # Show help
#   ./start_local.sh -i ./photo.jpg         # Start with an image for visual Q&A
#   ./start_local.sh --download Qwen/Qwen3-8B-GGUF --filename qwen3-8b-q4_k_m.gguf
#
# Author: Generated with love by Harei-chan (￣▽￣)ノ
# ============================================================================

set -e

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if running in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    # Try to activate local venv if it exists
    if [ -f ".venv/bin/activate" ]; then
        echo "Activating virtual environment..."
        source .venv/bin/activate
    elif [ -f "venv/bin/activate" ]; then
        echo "Activating virtual environment..."
        source venv/bin/activate
    fi
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Using Python $PYTHON_VERSION"

# Set environment variables for HuggingFace mirror (useful for China users)
# Uncomment the following line to use the mirror
# export HF_ENDPOINT="https://hf-mirror.com"

# Run the CLI
echo "Starting Qwen Chat CLI..."
echo "============================================"
python -m cli.main "$@"

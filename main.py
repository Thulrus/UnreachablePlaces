"""
Main entry point for running the unreachable mapper from command line.

Usage:
    python main.py [options]
"""
import sys
from src.cli import main

if __name__ == '__main__':
    sys.exit(main())

import sys
import os

# Ensure tests can import 'app' package when run from repo root or CI
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

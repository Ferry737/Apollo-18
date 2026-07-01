"""
Apollo 18 — Build Script for PyInstaller .EXE packaging.
Produces a single portable executable with all dependencies bundled.

Usage (on Windows):
    python packaging/build_exe.py

Or manually:
    pyinstaller --onefile --windowed --name Apollo18 ^
        --add-data "apollo18;apollo18" ^
        --hidden-import PyQt5 ^
        --hidden-import matplotlib.backends.backend_qt5agg ^
        --hidden-import onnxruntime ^
        main.py
"""
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build():
    """Build the .EXE using PyInstaller."""
    print("=" * 60)
    print("  Apollo 18 — Building Portable .EXE")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "Apollo18",
        f"--add-data", os.pathsep.join(["apollo18", "apollo18"]),
        "--hidden-import", "PyQt5",
        "--hidden-import", "PyQt5.QtCore",
        "--hidden-import", "PyQt5.QtGui",
        "--hidden-import", "PyQt5.QtWidgets",
        "--hidden-import", "matplotlib.backends.backend_qt5agg",
        "--hidden-import", "matplotlib.figure",
        "--hidden-import", "onnxruntime",
        "--hidden-import", "skl2onnx",
        "--collect-all", "ccxt",
        "--collect-all", "yfinance",
        "--noconfirm",
        "--clean",
        os.path.join(ROOT, "main.py"),
    ]

    print(f"\nRunning: {' '.join(cmd[:5])}...\n")
    result = subprocess.run(cmd, cwd=ROOT)

    if result.returncode == 0:
        exe_path = os.path.join(ROOT, "dist", "Apollo18.exe")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\n✅ Build successful!")
            print(f"   Output: {exe_path}")
            print(f"   Size: {size_mb:.1f} MB")
        else:
            print(f"\n✅ Build completed. Check dist/ folder.")
    else:
        print(f"\n❌ Build failed with exit code {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    build()

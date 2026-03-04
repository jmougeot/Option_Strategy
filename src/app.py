"""
Entry point for the PyQt6 version of M2O.

Usage:
    python -m myproject.app_qt
    or via run_qt.bat / run_qt.sh
"""


import multiprocessing
import sys
import os


def main() -> None:
    # Qt imports MUST be inside main() — NOT at module level.
    # multiprocessing.spawn re-imports app.py to bootstrap each subprocess;
    # if PyQt6 is imported at module level it crashes with 0xC0000005.
    import PyQt6
    real_plugins = os.path.join(os.path.dirname(PyQt6.__file__), "Qt6", "plugins")
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(real_plugins, "platforms")

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("M2O")
    app.setOrganizationName("BGC")

    # Import after QApplication is created
    from app.main_window import MainWindow

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()  # must be first line after __main__ guard
    main()

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
    import PyQt6
    
    real_plugins = os.path.join(os.path.dirname(PyQt6.__file__), "Qt6", "plugins")
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(real_plugins, "platforms")

    from PyQt6.QtWidgets import QApplication
    from app.theme import apply as apply_theme

    app = QApplication(sys.argv)
    app.setApplicationName("M2O")
    app.setOrganizationName("BGC")
    apply_theme(app)

    # Import after QApplication is created
    from app.main_window import MainWindow

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()  # must be first line after __main__ guard
    main()

"""AxisScope — minimal pen-plotter control app."""

import sys

from PySide6.QtWidgets import QApplication

from axiscope.views.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("AxisScope")
    app.setOrganizationName("AxisScope")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

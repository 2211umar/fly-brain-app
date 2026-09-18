import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel
)
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "Fruit Fly Brain Connectome Explorer"
        )

        self.resize(1200, 750)

        title = QLabel(
            "Fruit Fly Brain Connectome Explorer"
        )

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 28px;
                font-weight: bold;
            }
        """)

        self.setCentralWidget(title)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b1020;
            }
        """)


app = QApplication(sys.argv)

window = MainWindow()

window.show()

sys.exit(app.exec())
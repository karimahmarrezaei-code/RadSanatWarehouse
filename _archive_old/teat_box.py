import sys
from PyQt5.QtWidgets import QApplication
from app.ui.box_design_calculator import BoxDesignCalculator

app = QApplication(sys.argv)
window = BoxDesignCalculator()
window.show()
sys.exit(app.exec_())


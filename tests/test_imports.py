# main.py
# import sys

# from PySide6.QtWidgets import QApplication
# from datashop_toolbox.gui.rbr_to_odf_mainwindow import MainWindow
# from datashop_toolbox.gui.thermograph_gui_loader import ThermographMainWindow
# from datashop_toolbox.gui.odf_metadata_dialog import OdfMetadataDialog
# from datashop_toolbox.gui.rbr_profile_plot import PlotDialog
from datashop_toolbox.gui import rbr_profile_plot
from datashop_toolbox.historyhdr import HistoryHeader


def main():
    # app = QApplication(sys.argv)
    # w = ThermographMainWindow()
    # w = MainWindow()
    # w = OdfMetadataDialog()
    # w = PlotDialog()
    # w.show()
    # sys.exit(app.exec())

    hh = HistoryHeader()
    print(hh.print_object())

    rbr_profile_plot.main()


if __name__ == "__main__":
    main()
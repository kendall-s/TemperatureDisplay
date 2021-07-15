"""
This PyQt5 GUI app is used to display temperature data logged from a custom made temperature control unit
produced by Trevor Goodwin 2015 CSIRO. The unit outputs a string every second or so containing the temperature
along with other data.

"""

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5.QtWidgets import (QMainWindow, QGridLayout, QWidget, QApplication, QLabel, 
                            QComboBox, QPushButton, QLineEdit, QFrame, QAction, QFileDialog)
from PyQt5.QtCore import QThread, QObject, pyqtSignal
from PyQt5.QtGui import QFont
import pyqtgraph as pg
import sys 
import os
from pyqtgraph import colormap
import serial
import serial.tools.list_ports
import time
import random
import statistics


class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Some little setup for packaging into the exe with Pyinstaller
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        icon_path = 'centigrade.ico'
        self.setWindowIcon(QtGui.QIcon(f'{base_path}/{icon_path}'))

        # Init these as NANs
        self.folder_path = None
        self.ser = None
        self.measuring = False
        
        # Lists for the raw data
        self.plot_x = []
        self.plot_y = []

        # These are used for creating the 1 second median smoothed chart
        self.st = None
        self.count_back = 0
        self.smooth_plot_x = []
        self.smooth_plot_y = []

        # Startup functions
        self.init_ui()
        self.init_ports()
    
    def init_ui(self):
        """
        This function contains all of the UI setup, including the initialising of every
        widget and then placing them in the relevant locations of the grid layout
        """
        # Set the app wide font as Segoe UI (the windows 10 system font)
        self.setFont(QFont('Segoe UI'))
        self.setStyleSheet(""" QLabel { font: 14px; } QLineEdit { font: 14px } QComboBox { font: 14px } QPushButton { font: 14px } QCheckBox { font: 14px }""")
        # Create the grid layout and set the gutter spacing to 10px
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)

        # The following 6 lines are used to set the window size and then place it
        # in the center of the 'active' screen (user could be using a multi monitor setup)
        self.setGeometry(0, 0, 550, 300)
        qtRectangle = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())
        
        self.setWindowTitle('Temperature Logger')

        menu = self.menuBar()
        fileMenu = menu.addMenu('File')

        refresh_ports = QAction('Refresh Ports', self)
        refresh_ports.triggered.connect(self.init_ports)
        fileMenu.addAction(refresh_ports)

        # Start of the widgets initialisation

        ports_label = QLabel('<b>Select Port</b>')
        self.ports_combo = QComboBox()

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_port)
        self.connection_status = QLineEdit(" No Connection ")
        self.connection_status.setReadOnly(True)
        self.connection_status.setAlignment(QtCore.Qt.AlignCenter)
        self.connection_status.setStyleSheet("QLineEdit { background: rgb(224, 20, 0); color: rgb(250, 250, 250);}")
        self.connection_status.setFont(QFont('Segoe UI'))

        linesep_1 = QFrame()
        linesep_1.setFrameShape(QFrame.HLine)
        linesep_1.setFrameShadow(QFrame.Sunken)

        files_control_label = QLabel('<b>File Writing</b>')

        file_path_label = QLabel('File Path:')
        self.folder_path_lineedit = QLineEdit()
        self.folder_path_lineedit.setReadOnly(True)

        self.browse_path_button = QPushButton("Browse Path")
        self.browse_path_button.clicked.connect(self.browse_file_folder)

        files_name_label = QLabel('Files will be saved into the selected directory')
        files_name_label.setWordWrap(True)

        linesep_2 = QFrame()
        linesep_2.setFrameShape(QFrame.HLine)
        linesep_2.setFrameShadow(QFrame.Sunken)

        self.start_acquire = QPushButton("Acquire Data")
        self.start_acquire.clicked.connect(self.acquire_data)

        current_temp_label = QLabel('Current Temperature: ')
        current_temp_label.setStyleSheet("QLabel { font: 18px Segoe UI; }")
        self.current_temp = QLabel('0')
        self.current_temp.setStyleSheet("QLabel { font: 18px Segoe UI; }")

        stdev_temp_label = QLabel('Standard Deviation: ')
        stdev_temp_label.setStyleSheet("QLabel { font: 18px Segoe UI; }")
        self.stdev_temp = QLabel('0')
        self.stdev_temp.setStyleSheet("QLabel { font: 18px Segoe UI; }")

        # Set up the pyqt graph ready to go
        pg.setConfigOptions(antialias=True)
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setLabel('left', 'Temperature (C)')
        self.graphWidget.setLabel('bottom', 'Time')
        self.graphWidget.showGrid(x=True, y=True)
        self.graphWidget.setBackground('w')
        self.graphWidget.sizePolicy().setHorizontalStretch(2)

        graph_pen = pg.mkPen(color=(10, 10, 180))
        smooth_graph_pen = pg.mkPen(color=(10, 180, 10))
        

        # Add everything to our grid layout
        # Column 1
        grid_layout.addWidget(ports_label, 0, 0, 1, 2)
        grid_layout.addWidget(self.ports_combo, 1, 0, 1, 1)
        grid_layout.addWidget(self.connect_button, 1, 1, 1, 1)
        grid_layout.addWidget(self.connection_status, 2, 0, 1, 2)
        grid_layout.addWidget(linesep_1, 3, 0, 1, 2)

        grid_layout.addWidget(files_control_label, 4, 0, 1, 2)
        grid_layout.addWidget(file_path_label, 5, 0, 1, 1)
        grid_layout.addWidget(self.folder_path_lineedit, 6, 0, 1, 2)
        grid_layout.addWidget(self.browse_path_button, 7, 0, 1, 2)
        grid_layout.addWidget(files_name_label, 8, 0, 2, 2)


        grid_layout.addWidget(linesep_2, 10, 0, 1, 2)

        grid_layout.addWidget(self.start_acquire, 11, 0, 2, 2)

        # Column 2
        grid_layout.addWidget(current_temp_label, 0, 2)
        grid_layout.addWidget(self.current_temp, 0, 3)

        grid_layout.addWidget(stdev_temp_label, 0, 4)
        grid_layout.addWidget(self.stdev_temp, 0, 5)

        grid_layout.addWidget(self.graphWidget, 1, 2, 15, 12)

        # Set up our pyqtgraph widget with the 2 plottable lines
        self.plotted_data = self.graphWidget.plot(self.plot_x, self.plot_y, pen=graph_pen)
        self.smoothed_plotted_data = self.graphWidget.plot(self.smooth_plot_x, self.smooth_plot_y, pen=smooth_graph_pen)
        
        # Use open Gl for slightly better performance
        self.graphWidget.useOpenGL(True)
        
        # Set the layout of the application window widget to the grid layout which is holding everything
        self.centralWidget().setLayout(grid_layout)



    def init_ports(self):
        """
        Finds all the available com ports on the system, lists them in the combobox
        """
        ports = serial.tools.list_ports.comports()
        self.ports_combo.clear()
        for port in ports:
            self.ports_combo.addItem(str(port)[:15] + "...")
        
    def toggle_port(self):
        """
        This function is responsible for opening and closing the serial port 
        """
        port = self.ports_combo.currentText().split(" ")[0]
        print(port)

        if self.ser:
            print("Closing port")

            self.ser.close()
            self.ser = None

            self.connect_button.setText("Connect")
            self.connection_status.setText("No Connection")
            self.connection_status.setStyleSheet("QLineEdit { background: rgb(224, 20, 0); color: rgb(250, 250, 250);}")
        
        else:
            print("Opening port")
            #self.ser = 1
            try:
                self.ser = serial.Serial(timeout=1, baudrate=9600, stopbits=1, parity=serial.PARITY_NONE)
                self.ser.port = port
                self.ser.open()

                self.connect_button.setText("Disconnect")
                self.connection_status.setText("CONNECTED")
                self.connection_status.setStyleSheet("QLineEdit { background: rgb(15, 200, 53); color: rgb(250, 250, 250);}")
            except Exception:
                print('Error connecting to serial port')

    def browse_file_folder(self):
        """
        Allows the user to navigate to a folder so the file can be saved
        """
        folder_path = QFileDialog.getExistingDirectory(self, 'Select Folder')

        if os.path.exists(folder_path):
            self.folder_path = folder_path
            self.folder_path_lineedit.setText(folder_path)

    def acquire_data(self):
        """
        The majority of this function is just getting the input values and then checking if 
        the app is ready to capture data from the temperature logger. It then sets up the new thread
        with the DataAcquirer object and primes it for data capture.
        """

        # Get all of the required values from the fields
        folder_path = self.folder_path_lineedit.text()

        if not self.measuring:
            if self.ser:
                if len(folder_path) > 0:
                    self.start_acquire.setText("Stop Acquire")
                    self.ser.flushOutput()

                    print(self.ser.inWaiting())

                    # Initiate the data acquisition object and start the loop
                    self.measuring = True
                    self.thread = QThread()
                    self.data_thread = DataAcquirer(self.ser, folder_path)
                    self.data_thread.moveToThread(self.thread)
                    self.thread.started.connect(self.data_thread.data_acquire_loop)
                    self.data_thread.finished.connect(self.thread.quit)
                    self.data_thread.new_data.connect(self.update_chart)

                    # Disable all of the buttons so that I don't have to add checking to their functions
                    self.connect_button.setEnabled(False)
                    self.browse_path_button.setEnabled(False)

                    self.thread.start()
                else:
                    print('Please browse to a folder first')
            else:
                print('There is not a current serial connection!')
        else:
            self.start_acquire.setText("Start Acquire")
            # This will stop the data acquisition loop
            self.measuring = False
            self.data_thread.measuring = False
            
            # Renable everything when acquisition has stopped
            self.connect_button.setEnabled(True)
            self.browse_path_button.setEnabled(True)

            self.toggle_port()

    def update_chart(self, new_data):
        """
        Class method that will add the newly collected data to the plot,
        this will also create a median smoothed dataset every 1 second and add it to the chart
        """
        # Once we have a lot of data in the lists, start removing points so that the 
        # app stays performant
        if len(self.plot_x) == 4000:
            self.plot_x.pop(0)
            self.plot_y.pop(0)

        # Add the latest raw data to the raw plot lists
        self.plot_x.append(new_data[1])
        self.plot_y.append(new_data[0])

        # Update the raw chart and display the latest signal value
        self.plotted_data.setData(self.plot_x, self.plot_y)

        self.current_temp.setText(f'{new_data[0]} °C')
        if len(self.plot_y) > 2:
            self.stdev_temp.setText(f'{round(statistics.stdev(self.plot_y), 4)} °C')


class DataAcquirer(QObject):
    """
    The DataAcquirer class is created and used in a separate thread to capture data continually 
    from the serial device, it uses the PyQt signals and slots to communicate data back to the main UI thread
    """
    new_data = pyqtSignal(list)
    finished = pyqtSignal()
    
    def __init__(self, serial_object, folder_path):
        super().__init__()
        self.measuring = True
        self.serial_object = serial_object
        self.folder_path = folder_path

        self.file_path = folder_path + f"/temperature_log_{time.time()}.csv"
        self.raw_data = []
        self.raw_time_data = []
        
    def data_acquire_loop(self):
        """ This is the main data acquisition loop - this will run while the class variable measuring is True"""
        clear = self.serial_object.inWaiting()

        while self.measuring:
            f = open(self.file_path, "a")
            print('Data acquiring')
            try:
                string_sent = self.serial_object.readline()

                string_sent = str(string_sent)

                if 'T' in string_sent:
                    t_index = string_sent.find('T')
                    temperature = float(string_sent[t_index + 2:t_index + 9])
                    time_now = time.time()
                    time_now_fmt = time.strftime('%d/%m/%Y %H:%M:%S +0000', time.gmtime())
                    data = [temperature, time_now]

                    self.new_data.emit(data)
                    f.write(f'{temperature}, {time_now}, {time_now_fmt}\n')

                else:
                    print('No data in string, lets move on')

                time.sleep(0.25)
            except Exception:
                print('Error connecting to the serial device')
                time.sleep(10)

        f.close()
        self.finished.emit()

def main():
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
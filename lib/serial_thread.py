from PySide6.QtCore import QThread
from PySide6.QtWidgets import QDialog
from PySide6.QtGui import QIcon
from lib.donnees import *
from lib.ui_dialog import Ui_Dialog

import serial
import serial.tools.list_ports
import time

class SerialThread(QThread):
    # message_received = Signal(bytes)
    def __init__(self, port = None, baudrate = None):
        super().__init__()
        if port is not None:
            self.port = port
            self.baudrate = baudrate
            self.serial = serial.Serial(port, baudrate)
            self.running = True
        else:
            self.port = None
            self.baudrate = None
            self.serial = None
            self.running = False

        self.stateRx = 0
        self.compteurData = 0

        self.lastTime = time.time()

        self.msgError = ""

    def run(self):
        while self.running:
            if self.serial.in_waiting > 0:
                data = self.serial.read(1)
                # print(data)
                # self.message_received.emit(data)
                self.RxReceive(data)
                # self.serial.write(b'\xFF')
                # sample_message = Message(id=1, length=3, data=[0x01, 0x02, 0x03])
                # packet = sample_message.build_packet()
                # self.serial.write(packet)
            if((time.time()-self.lastTime) > 3):
                self.lastTime = time.time()
                if(com.ecritureEnCours):
                    com.ecritureEnCours = False
                    self.serial.cancel_write() #Pour debloquer toutes les 3 secondes si jamais il y a un probléme
                    com.problemeEnEcriture = True
            

    def close(self):
        if self.running:
            self.running = False
            self.serial.close()
    
    # def send_data(self, data):
    #     if self.running:
    #         try:
    #             self.serial.write(data)
    #         except serial.SerialException as e:
    #             print(f"Failed to send data: {e}")
    #             self.close()
    #             self.running = False

    # @Slot(bytes)
    def RxReceive(self, message):
        byte = int.from_bytes(message, byteorder='big', signed=False)
        # self.ui.textEdit_panel.append(f"Received: {byte}")
        print(f"Received: {message}")
        match self.stateRx:
            case 0:
                if byte == 0xff:
                    self.msgError = ""
                    self.msgError += " Header"
                    # print("Header")
                    self.stateRx = 1
                    com.rxMsg[com.FIFO_Ecriture].checksum = 0
            case 1:
                # print("ID")
                self.msgError += " ID" + str(byte.to_bytes())
                com.rxMsg[com.FIFO_Ecriture].id = int(byte)
                com.rxMsg[com.FIFO_Ecriture].checksum ^= byte
                self.stateRx = 2
            case 2:
                # print("len")
                self.msgError += " len" + str(byte.to_bytes())
                com.rxMsg[com.FIFO_Ecriture].len = int(byte)
                com.rxMsg[com.FIFO_Ecriture].checksum ^= byte
                com.rxMsg[com.FIFO_Ecriture].data = []
                self.compteurData = 0
                self.stateRx = 3
            case 3:
                # print("data n°", self.compteurData)
                self.msgError += " dt[" + str(self.compteurData) + "]= " + str(byte.to_bytes()) +"."
                com.rxMsg[com.FIFO_Ecriture].data.append(int(byte)) 
                com.rxMsg[com.FIFO_Ecriture].checksum ^= byte
                self.compteurData += 1
                if(self.compteurData >= com.rxMsg[com.FIFO_Ecriture].len):
                    self.compteurData = 0
                    self.stateRx = 4
            case 4:
                # print("checksum %d", byte)
                self.msgError += " checksum" + str(byte.to_bytes())
                if(com.rxMsg[com.FIFO_Ecriture].checksum == int(byte)):
                    self.stateRx = 5
                else :
                    self.stateRx = 0
                    print(self.msgError)
                    print(" ERROR Checksum mismatch msg n°"+ str(com.FIFO_Ecriture) +", "+ str(com.rxMsg[com.FIFO_Ecriture].checksum) + " != " + str(byte))
            case 5:
                # print("Header Fin")
                if byte == 0xFF:
                    self.msgError += " Header Fin"
                    print("Received new msg n°"+ str(com.FIFO_Ecriture) +" from id : ", com.rxMsg[com.FIFO_Ecriture].id.to_bytes())
                    com.FIFO_Ecriture = (com.FIFO_Ecriture + 1)%SIZE_FIFO
                print(self.msgError)
                self.stateRx = 0


class SelectCOM(QDialog):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window  # Stocker la référence à MainWindow
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle("CHOIX PORT COM")
        self.setWindowIcon(QIcon('logo.ico'))
        # self.ui.buttonBox.accepted.connect(self.start_serial) #Cas si jamais on n'appuie sur OK. Fonction dans la mainwindow pour afficher à l'utilisateur ce qu'on a fait
        self.ui.buttonBox.accepted.connect(self.main_window.start_serial)
        self.ui.buttonBox.rejected.connect(self.reject) #Cas si jamais on n'appuie sur annuler

        self.populate_com_ports()

    def populate_com_ports(self):
        self.ui.comboBox.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.ui.comboBox.addItem(port.device)

    def start_serial(self):
        selected_port = self.ui.comboBox.currentText()
        print(selected_port)
        if selected_port:
            try:
                com.serial_thread = SerialThread(selected_port, SERIAL_BAUDRATE)
                com.serial_thread.start()
                print("Starting serial com")
                self.accept()
            except serial.SerialException as e:
                print("Serial Error", f"Failed to open port {selected_port}: {e}")
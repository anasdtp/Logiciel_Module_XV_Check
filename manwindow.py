import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon

import serial
import serial.tools.list_ports
from lib.serial_thread import SerialThread, SelectCOM

from lib.ui_mainwindow import Ui_MainWindow

from lib.donnees import *

#Pour actualiser : 
#   pyside6-rcc -o Ressources_rc.py Ressources.qrc
#   pyside6-uic mainwindow.ui -o ui_mainwindow.py
#   pyside6-uic dialog.ui -o ui_dialog.py
#   pyside6-uic tableauBilan.ui -o ui_tableauVoies.py
#   pyside6-uic ficheValidation.ui -o ui_ficheValidation.py
#   pyside6-uic ajoutControleur.ui -o ui_ajoutControleur.py 
#   pyside6-uic selectionneur_voies.ui -o ui_selectionneur_voies.py


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Banc de test carte ARAL")
        self.setWindowIcon(QIcon('logo.ico'))

        self.serial_window = SelectCOM(self)
        
        self.ui.action_Quit.triggered.connect(self.QuitWindows)
        self.ui.action_Clear_Log.triggered.connect(self.textPanel_Clear)
        self.ui.action_Connect.triggered.connect(self.openDialogWindow)
        self.ui.action_Disconnect.triggered.connect(self.closeSerial)
        self.ui.action_Refresh.triggered.connect(self.refreshSystem)
        
        self.ui.sendButton_trame_brute.clicked.connect(self.onSendButtonTrameBrute)
        
        print("End Initialization MainWindow")

    
    def start_serial(self):
        selected_port = self.serial_window.ui.comboBox.currentText()
        print(selected_port)
        if selected_port:
            try:
                com.serial_thread = SerialThread(selected_port, SERIAL_BAUDRATE)
                com.serial_thread.start()
                print("Starting serial com")
                self.ui.textEdit.append(f"")
                self.ui.textEdit.append(f"-----------Starting serial com")
                self.ui.textEdit.append(f"-----------Port: {selected_port}")
                self.serial_window.accept()
            except serial.SerialException as e:
                print("Serial Error", f"Failed to open port {selected_port}: {e}")
                self.ui.textEdit.append(f"")
                self.ui.textEdit.append(f"-----------Serial Error !!")
                self.ui.textEdit.append(f"-----------Failed to open port {selected_port}: {e}")


    def sendMsg(self, msg = Message()):
        # sample_message = Message(id=1, length=3, data=[0x01, 0x02, 0x03])
        packet = msg.build_packet()
        print(packet)
        if com.serial_thread.running:
            try:
                com.ecritureEnCours = True
                com.serial_thread.serial.write(packet) #Fonction bloquante, qui se debloque toutes les 3 secondes si l'envoi à echouer
                com.ecritureEnCours = False
                if(com.problemeEnEcriture):
                    com.problemeEnEcriture = False
                    self.ui.textEdit.append(f"")
                    self.ui.textEdit.append(f"-----------Problème rencontré lors de l'envoi de données")
                    self.ui.textEdit.append(f"-----------Deconnexion du PORT COM...")
                    com.serial_thread.close()
                    self.ui.textEdit.append(f"-----------Essayer de vous reconnectez svp")
            except (serial.SerialException) as e:
                error_message = f"Failed to send data: {e.__class__.__name__}: {e}"
                print(error_message)
                self.ui.textEdit.append(f"")
                self.ui.textEdit.append(f"-----------{error_message}")
                com.serial_thread.close()
                self.ui.textEdit.append(f"-----------Essayer de vous reconnectez svp")
        else:
            self.ui.textEdit.append(f"")
            self.ui.textEdit.append(f"-----------Aucun PORT COM de connecté! Veuillez-vous connectez.")
                
    def sendEmpty(self, id):
        sample_message = Message(id, length=0, data=[0])
        self.sendMsg(sample_message)

    def sendByte(self, id, byte):
        sample_message = Message(id, length=1, data=[byte & 0xFF])
        self.sendMsg(sample_message)

    def sendTwoBytes(self, id, bytes):
        sample_message = Message(id, length=2, data=[(bytes&0xFF), (bytes>>8 & 0xFF)])
        self.sendMsg(sample_message)
    
    def sendTrame(self, msg = FreqMessage()):
        sample_message = Message(ID_TX_FRAME, length=3, data=[msg.adr, msg.cmd1, msg.cmd0])
        self.sendMsg(sample_message)
    

    def textPanel_Clear(self):
        self.ui.textEdit.clear()
    
    def closeSerial(self):
        self.ui.textEdit.append(f"")
        self.ui.textEdit.append(f"-----------Deconnexion du PORT COM...")
        com.serial_thread.close()
    
    def openDialogWindow(self):
        self.serial_window.show()
        self.serial_window.raise_()
        self.serial_window.activateWindow()
        self.serial_window.populate_com_ports() #Permet d'aller chercher et actualiser les ports COM de disponible. Ce qui permet de ne pas evoir fermer le logiciel et le reouvrir
    
    def refreshSystem(self):
        print("Rafraichissement du systeme")
        self.ui.textEdit.append(f"")
        self.ui.textEdit.append(f"-----------Rafraichissement du systeme")
        #... 
        #Fonction à completer
    
    def onSendButtonTrameBrute(self):
        msg = FreqMessage()
        msg.trame[0] = int(self.ui.comboBox_trame_1.currentText(), 16)
        msg.trame[1] = int(self.ui.comboBox_trame_2.currentText(), 16)  
        msg.trame[2] = int(self.ui.comboBox_trame_3.currentText(), 16)
        msg.trame[3] = int(self.ui.comboBox_trame_4.currentText(), 16)
        msg.trame[4] = int(self.ui.comboBox_trame_5.currentText(), 16)
        msg.trame[5] = int(self.ui.comboBox_trame_6.currentText(), 16)
        msg.parse_trame()
        self.ui.textEdit.append(f"")
        self.ui.textEdit.append(f"-----------Envoi de la trame brute : " + msg.toString())
        self.sendTrame(msg)
    
    def closeEvent(self, event):
        print("Au revoir")
        self.serial_window.close()
        
        # self.switchARAL.close()
        super().closeEvent(event)
        
    def QuitWindows(self):
        self.close()
        QApplication.quit()
           
           
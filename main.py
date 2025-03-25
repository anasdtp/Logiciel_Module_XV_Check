from manwindow import *

class Application(MainWindow):
    def __init__(self):
        super().__init__()
        
        if com.serial_thread is None:
            com.serial_thread = SerialThread()  
        # Configuration du QTimer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.RxManage)
        self.timer.start(1)  # Déclenchement toutes les 1 ms
        
        self.FIFO_lecture = 0
        self.FIFO_occupation = 0
        self.FIFO_max_occupation = 0
        
        self.adresse_module = 0x21 #Adresse du module avec lequel on veut communiquer
        self.mode_de_fontionnement = "LIGNE" #Mode de fonctionnement du banc de test : LIGNE ou TEST. 
        #En mode LIGNE, le banc de test ne fait que recevoir les trames des modules et les affiches
        #En mode TEST, le banc de test renvoi un acquittement à chaque trame reçu et si l'adresse du module correspond à celle du banc de test, 
        #on traite la trame et on renvoi une trame de retour par rapport au protocole de communication des modules 8 voies
    
    def RxManage(self):
        # print("RxManage")
        self.FIFO_occupation = com.FIFO_Ecriture - self.FIFO_lecture
        if(self.FIFO_occupation<0):
            self.FIFO_occupation = self.FIFO_occupation + SIZE_FIFO
        if(self.FIFO_max_occupation < self.FIFO_occupation):
            self.FIFO_max_occupation = self.FIFO_occupation
        if(self.FIFO_occupation == 0):
            return

        id = com.rxMsg[self.FIFO_lecture].id
        match id:
            case id if (id == ID_ACK_GENERAL):
                message = f"ID_ACK_GENERAL : reponse gen"#, " + idComEnText[com.rxMsg[self.FIFO_lecture].data[0]] + " : " + str(com.rxMsg[self.FIFO_lecture].data[0])
                if(com.rxMsg[self.FIFO_lecture].len > 0):
                    message += ", " + idComEnText[com.rxMsg[self.FIFO_lecture].data[0]] + " : "
                    for i in range(1, com.rxMsg[self.FIFO_lecture].len):
                        message += str(com.rxMsg[self.FIFO_lecture].data[i]) + ", "
                self.ui.textEdit.append(f"")
                self.ui.textEdit_ACK.append(f"")
                self.ui.textEdit.append(message)
                self.ui.textEdit_ACK.append(message)

            case id if (id == ID_REPEAT_REQUEST):
                message = f"ID_REPEAT_REQUEST : le banc de test n'a pas compris, message incohérent"
                self.ui.textEdit.append(f"")
                self.ui.textEdit.append(message)
                
            case id if (id == ID_RX_FRAME):
                msg = FreqMessage()
                msg.adr = com.rxMsg[self.FIFO_lecture].data[0]
                msg.cmd1 = com.rxMsg[self.FIFO_lecture].data[1]
                msg.cmd0 = com.rxMsg[self.FIFO_lecture].data[2]
                msg.build_trame()
                
                message = f"ID_RX_FRAME : trame reçu des modules : " + msg.toString() # A afficher dans un autre textEdit
                self.ui.textEdit.append(f"")
                self.ui.textEdit.append(message)
                
                self.manageTrame(msg)
            
            case _:
                self.ui.textEdit.append(f"Received message from an unknown ID : " + str(id))
        self.FIFO_lecture = (self.FIFO_lecture + 1) % SIZE_FIFO

    def manageTrame(self, msg : FreqMessage):
        #je recois une trame, msg.adr est l'adresse du module qui m'envoie la trame
        #msg.cmd1 et msg.cmd0 sont les 2 octet de commande envoyées par le module
        #il faut etudier le protocole de communication des modules 8 voies pour savoir comment traiter les trames recues
        
        self.ui.textEdit.append(f"")#Fonction pour afficher la console du logiciel
        self.ui.textEdit.append(f"-----------Trame recu : " + msg.toString())
            
        if(self.mode_de_fontionnement == "TEST"):
            self.sendTrame(msg) #Si on est en mode test on renvoi l'ack
            
            if(msg.adr == self.adresse_module): #Si l'adresse du module est celle du banc de test, on traite la trame
                #traitement de la trame
                msg_en_retour = FreqMessage()
                msg_en_retour.adr = self.adresse_module
                msg_en_retour.cmd1 = 0x00
                msg_en_retour.cmd0 = 0x00
                msg_en_retour.build_trame()
                
                
                self.ui.textEdit.append(f"-----------Traitement de la trame...")
                self.ui.textEdit.append(f"-----------Envoi de la trame de retour...")
                self.sendTrame(msg_en_retour)  
                
                #Pour faire une machine d'etat, tu peux utiliser "match ... case" pour traiter les trames reçues
                #Tu dois aller chercher dans le pdf du protocole de communication des modules 8 voies pour savoir comment traiter les trames
        
        


def main():
    print("Hello")
    app = QApplication([]) 
    
    main_window = Application()
    main_window.show()

    main_window.serial_window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()

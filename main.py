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
    
    def sendTestModule(self, adresse_module):
        # Envoi d’un message de test du module
        msg = FreqMessage(adresse_module, 0xD9, adresse_module)
        msg.build_trame()
        self.sendTrame(msg) 
    
    def sendReset(self, adresse_module):
        # Envoi d’un message de réinitialisation du module
        pass
    
    def sendInhibition(self, adresse_module, states_voies):
        voies = ModuleVoies(states_voies)
        msg = voies.toFreqMessage(adresse_module, 0x0)
        self.sendTrame(msg)
    
    # def sendAlarmes(self, adresse_module, states_voies): #inutile car le banc de test ne doit pas envoyer de l'etat de ses voies, il en a pas
    #     voies = ModuleVoies(states_voies)
    #     msg = voies.toFreqMessage(adresse_module, 0xA)
    #     self.sendTrame(msg)
    
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
                
                message = f"ID_RX_FRAME : trame reçu des modules : " + str(msg) # A afficher dans un autre textEdit
                self.ui.textEdit.append(f"")
                self.ui.textEdit.append(message)
                
                self.manageTrame(msg)
            
            case _:
                self.ui.textEdit.append(f"Received message from an unknown ID : " + str(id))
        self.FIFO_lecture = (self.FIFO_lecture + 1) % SIZE_FIFO
    
    def manageTrame(self, msg: FreqMessage):
        self.ui.textEdit.append("")
        self.ui.textEdit.append(f"-----------Trame reçue : {str(msg)}")

        if self.mode_de_fontionnement == "TEST":
            # Envoi d’un ACK en mode TEST
            self.sendTrame(msg)

            # Vérifier si la trame est destinée à ce module
            if msg.adr == self.adresse_module:
                self.ui.textEdit.append("-----------Traitement de la trame pour ce module...")
                
                # Vérifier le type de message reçu
                match msg.trame[2]:
                    case 0xA:  # Message d’alarme
                        self.ui.textEdit.append("→ Message d’alarme détecté.")
                        
                        # Conversion du message en objet ModuleVoies
                        voies = ModuleVoies()
                        voies.fromFreqMessage(msg)
                        
                        # Affichage des alarmes détectées
                        self.ui.textEdit.append(str(voies))
                    
                    # case 0xD:  # Test du module #Cas qu'on ne devrait pas recevoir car c'est le banc de test qui envoie ce message
                    #     self.ui.textEdit.append("→ Test du module détecté.")
                        
                    #     # Extraire le numéro du module testé
                    #     module_tested = (msg.trame[0] << 4) | msg.trame[1]
                        
                    #     self.ui.textEdit.append(f"Test demandé pour le module {module_tested:02X}")
                        
                    #     # Réponse au test
                    #     msg_en_retour.trame = [msg.trame[0], msg.trame[1], 0xD, 0x9, msg.trame[0], msg.trame[1]]
                    
                    case 0x8:  # Le module s'est réinitialisé
                        self.ui.textEdit.append("→ Réinitialisation du module détectée.")

                    case 0xB: #Defaut 220V, message identique à un message d'alarme sauf le code B à la place de A
                        self.ui.textEdit.append("→ Défaut 220V détecté.")
                        
                        # Conversion du message en objet ModuleVoies
                        voies = ModuleVoies()
                        voies.fromFreqMessage(msg)
                        
                        # Affichage des alarmes détectées
                        self.ui.textEdit.append(str(voies))
                        
                    case _:  # Cas inconnu
                        self.ui.textEdit.append("Commande inconnue.")




def main():
    print("Hello")
    app = QApplication([]) 
    
    main_window = Application()
    main_window.show()

    main_window.serial_window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
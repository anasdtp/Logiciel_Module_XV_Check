
import struct

SERIAL_BAUDRATE = 921600

ID_ACK_GENERAL = 0xC0 #Ack pour tous le reste
ID_REPEAT_REQUEST = 0xD0

ID_RX_FRAME     = 0xA0 #On envoit la trame reçu des modules au pc
ID_TX_FRAME     = 0xA1 #On envoit la trame reçu du pc aux modules

idComEnText = {
    0 : "",
    0xC0 : "ID_ACK_GENERAL",
    0xD0 : "ID_REPEAT_REQUEST",
    0xA0 : "ID_RX_FRAME",
    0xA1 : "ID_TX_FRAME",
}

class Message():
    def __init__(self, id=0, length=0, data=None, checksum=0):
        self.id = id
        self.len = length
        self.data = data if data else []
        self.checksum = checksum

    def build_packet(self):
        # Calculate checksum as a simple example
        self.checksum = (self.id ^ self.len) & 0xFF
        for i in range(self.len):
            self.checksum ^= self.data[i]
        length = self.len if(self.len) else 1
        # Construct the packet with start marker, ID, length, data, checksum, and end marker
        packet_format = f'<B B B {length}s B B'
        packet_data = bytes(self.data)
        return struct.pack(packet_format, 0xFF, self.id, self.len, packet_data, self.checksum, 0xFF)

SIZE_FIFO = 32
class COMMUNICATION():
    def __init__(self):
        self.rxMsg = [Message() for _ in range(SIZE_FIFO)]
        self.FIFO_Ecriture = 0
        self.serial_thread = None
        self.ecritureEnCours = False #Flag pour faire savoir qu'on a lancé une ecriture
        self.problemeEnEcriture = False #Flag pour dire que le serial.write n'a pas fonctionné
com = COMMUNICATION()

class FreqMessage():
    def __init__(self, adr=0, cmd1=0, cmd0=0):
        self.adr = adr & 0xFF  # Ensure adr is within 8 bits
        self.cmd1 = cmd1 & 0xFF  # Ensure cmd1 is within 8 bits
        self.cmd0 = cmd0 & 0xFF  # Ensure cmd0 is within 8 bits
        
        self.trame = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]

    def parse_trame(self):
        self.adr  = ((self.trame[0] << 4)& 0xF0) | (self.trame[1] & 0x0F)
        self.cmd1 = ((self.trame[2] << 4)& 0xF0) | (self.trame[3] & 0x0F)
        self.cmd0 = ((self.trame[4] << 4)& 0xF0) | (self.trame[5] & 0x0F)

    def build_trame(self):
        self.trame[0] = (self.adr  >> 4)& 0x0F
        self.trame[1] = self.adr        & 0x0F
        self.trame[2] = (self.cmd1 >> 4)& 0x0F
        self.trame[3] = self.cmd1       & 0x0F
        self.trame[4] = (self.cmd0 >> 4)& 0x0F
        self.trame[5] = self.cmd0       & 0x0F

    def __str__(self):
        return f"F{self.adr:02X}{self.cmd1:02X}{self.cmd0:02X}F"
    
class ModuleVoies:
    def __init__(self, states: list = None):
        """
        states : liste de 9 booléens représentant l'état des voies V9 à V1. (V9 = defaut technique)
                 True = voie activée, False = voie désactivée.
        """
        if states is None:
            self.states = [False] * 9
        else:
            if len(states) != 9:
                raise ValueError("La liste 'states' doit contenir 9 éléments (V9 à V1)")
            self.states = states

    @classmethod
    def fromFreqMessage(cls, msg: FreqMessage):
        """
        Convertit un FreqMessage en objet ModuleVoies.
        On suppose que msg.trame est une liste de 6 nibbles organisés ainsi :
          - msg.trame[0] : X (1ère partie de l'adresse)
          - msg.trame[1] : Y (2ème partie de l'adresse)
          - msg.trame[2] : Type de message (pour une alarme, ce sera 0xA)
          - msg.trame[3] : 0 V9 V8 V7
          - msg.trame[4] : 0 V6 V5 V4
          - msg.trame[5] : 0 V3 V2 V1
        """
        # Extraction des états en partant de V9 (MSB) jusqu'à V1 (LSB)
        states = []
        # Pour msg.trame[3] : extraire V9, V8, V7
        for shift in (2, 1, 0):
            states.append(bool((msg.trame[3] >> shift) & 0x01))
        # Pour msg.trame[4] : extraire V6, V5, V4
        for shift in (2, 1, 0):
            states.append(bool((msg.trame[4] >> shift) & 0x01))
        # Pour msg.trame[5] : extraire V3, V2, V1
        for shift in (2, 1, 0):
            states.append(bool((msg.trame[5] >> shift) & 0x01))
        return cls(states)

    def toFreqMessage(self, module_address: int, message_type: int) -> FreqMessage:
        """
        Convertit l'état des voies (self.states) en un FreqMessage.
        module_address : adresse du module (octet) à placer dans les 2 premiers nibbles.
        message_type   : valeur du 3ème ton (par exemple 0xA pour une alarme).
        
        L'organisation du FreqMessage généré est la suivante :
          - trame[0] : partie haute de l'adresse (module_address >> 4)
          - trame[1] : partie basse de l'adresse (module_address & 0x0F)
          - trame[2] : type de message (message_type)
          - trame[3] : 0 V9 V8 V7\n          - trame[4] : 0 V6 V5 V4\n          - trame[5] : 0 V3 V2 V1
        """
        # Création du FreqMessage avec les valeurs par défaut
        msg = FreqMessage(adr=module_address)
        msg.build_trame()
        msg.trame[2] = message_type
        
        # Packager les états par groupe de 3 bits
        # Les 3 premiers éléments de self.states correspondent à V9, V8, V7
        msg.trame[3] = ((1 if self.states[0] else 0) << 2) | ((1 if self.states[1] else 0) << 1) | (1 if self.states[2] else 0)
        # Les 3 suivants correspondent à V6, V5, V4
        msg.trame[4] = ((1 if self.states[3] else 0) << 2) | ((1 if self.states[4] else 0) << 1) | (1 if self.states[5] else 0)
        # Les 3 derniers correspondent à V3, V2, V1
        msg.trame[5] = ((1 if self.states[6] else 0) << 2) | ((1 if self.states[7] else 0) << 1) | (1 if self.states[8] else 0)
        
        msg.parse_trame()
        
        return msg

    def __str__(self):
        """
        Affichage de l'état des voies de V9 à V1.
        """
        s = "Voies : "
        for i, etat in enumerate(self.states):
            voie = 9 - i
            s += f"V{voie}={'ON' if etat else 'OFF'}  "
        return s



def testFreqMessage():
    print("-----Test de la classe FreqMessage")
    msg = FreqMessage(0x21, 0xD9, 0x21)
    msg.build_trame()
    print("", "".join(f"{byte:X}" for byte in msg.trame))
    
    print(msg)
    print(str(msg))
    var = str(msg)
    print(var)


def testModuleVoies():
    print("-----Test de la classe ModuleVoies")
    # Exemple de FreqMessage d'alarme reçu
    # Module adresse 0x21, type message = 0xA, et alarmes sur quelques voies
    # Par exemple, supposons :
    #   - msg.trame[3] = 0b101  (V9=1, V8=0, V7=1)
    #   - msg.trame[4] = 0b010  (V6=0, V5=1, V4=0)
    #   - msg.trame[5] = 0b111  (V3=1, V2=1, V1=1)
    msg = FreqMessage()
    msg.trame = [0x2, 0x1, 0xA, 0b101, 0b010, 0b111]
    msg.parse_trame()
    print(msg)
    
    print("----------Conversion de la trame en objet ModuleVoies")
    voies = ModuleVoies.fromFreqMessage(msg)
    print(voies)  # Affiche l'état des voies

    print("----------Création d'une trame de message à partir des voies")
    # Ici, on souhaite envoyer un message de type alarme (0xA) pour le module 0x21
    msg2 = voies.toFreqMessage(module_address=0x21, message_type=0xA)
    print(msg2)
    
    
    print("----------Création d'un objet ModuleVoies à partir d'une liste d'états")
    # Création d'un objet ModuleVoies avec quelques voies activées
    voies2 = ModuleVoies([True, False, False, False, False, True, True, False, False])
    print(voies2)
    print("----------Création d'une trame de message à partir des voies")
    msg3 = voies2.toFreqMessage(module_address=0x21, message_type=0xA)
    print(msg3)

if __name__ == '__main__':
    testFreqMessage()
    testModuleVoies()
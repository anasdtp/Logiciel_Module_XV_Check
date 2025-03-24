
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

class FreqMessage:
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

    def toString(self):
        return f"F{self.adr:02X}{self.cmd1:02X}{self.cmd0:02X}F"
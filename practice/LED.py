import pyfirmata2
from time import sleep

PORT =  pyfirmata2.Arduino.AUTODETECT
board = pyfirmata2.Arduino(PORT)
digital_out_13 = board.get_pin('d:13:o')

for i in range(10):
    digital_out_13.write(True)
    sleep(1)
    digital_out_13.write(False)
    sleep(1)

board.exit()

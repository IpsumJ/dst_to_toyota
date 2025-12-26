#!/usr/bin/env python
import serial
import sys
import math
from embfile import EmbFile

class SerialComError(Exception):
    pass

class ToyotaCom():
    def __init__(self, serial_port):
        self.ser = serial.Serial(
            port = serial_port,
            baudrate = 9600,
            bytesize = serial.EIGHTBITS,
            parity = serial.PARITY_ODD,
            stopbits = serial.STOPBITS_TWO,
            timeout = 30,
            rtscts = True
        )
        self._send_blocks = 0
        self._blocks_to_send = 1
        if not self.ser.is_open:
            raise SerialComError('Ser not open')

    def send(self, data, colors):
        if not self.ser.is_open:
            raise SerialComError('Ser not open')
        
        start = self.ser.read(2)
        if len(start) < 2:
            raise SerialComError('Timeout, abort')
        if start != b'\x92\x01':
            raise SerialComError('Unexpected start message, wrong dataset number?')

        self.ser.write(bytes([0x52, 0x00, colors, 0x01]))

        ack = self.ser.read(1)
        if len(ack) < 1:
            raise SerialComError('Timeout, abort')
        if ack != b'\x94':
            raise SerialComError('Not an ACK message')
        
        data = bytearray(data)
        self._send_blocks = 0
        self._blocks_to_send = math.ceil(len(data) / 300)
        while len(data) > 0:
            self._send_blocks += 1
            if self._send_blocks >= 0xff:
                raise SerialComError('too many blocks')
            block = data[:300]
            del data[:300]

            self.ser.write(bytes([0x54, 0x00, 0x03, 0x01, self._send_blocks, 0x00]))
            self.ser.write(block)
            self.ser.write(b'\xAA')

            ack = self.ser.read(1)
            if len(ack) < 1:
                raise SerialComError('Timeout, abort')
            if ack == b'\x94':
                continue
            if ack == b'\x93':
                if len(data) != 0:
                    print(f'Machine indicates end but data is not empty {len(data)}')
                break

        ack = self.ser.read(1)
        if len(ack) < 1:
            raise SerialComError('Timeout, abort')
        if ack != b'\x01':
            raise SerialComError('Not an ACK message')
        
        self.ser.write(bytes([0x53, 0x00, 0x01, 0x01]))

    def progress(self):
        return self._send_blocks / self._blocks_to_send

    def close(self):
        self.ser.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage:')
        print(f'    {sys.argv[0]} Serial_Port colors File_to_Send.10o')
        print(f'or: {sys.argv[0]} Serial_Port File_to_Send.dst')
        exit(1)

    if len(sys.argv) == 4:
        colors = int(sys.argv[2])

        with open(sys.argv[3], 'rb') as f:
            data = f.read()
    else:
        with open(sys.argv[2], 'rb') as f:
            dst_data = f.read()
        emb = EmbFile()
        emb.load_dst(dst_data)

        print(emb.colors, 'Colors', len(emb._stitches), 'Stitches')

        emb.plot()
        data = emb.to10o()
        colors = emb.colors

    tcom = ToyotaCom(sys.argv[1])
    tcom.send(data, colors)
    tcom.close()

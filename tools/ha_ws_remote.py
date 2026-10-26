"""HA WebSocket helper, executed inside the existing SSH add-on; stdlib only."""
import base64
import hashlib
import json
import os
import socket
import struct

class HAWebSocket:
    def __init__(self):
        self.sock = socket.create_connection(('supervisor', 80), timeout=20)
        self.file = self.sock.makefile('rb')
        self.counter = 0
        key = base64.b64encode(os.urandom(16)).decode()
        request = ('GET /core/websocket HTTP/1.1\r\nHost: supervisor\r\n'
                   'Upgrade: websocket\r\nConnection: Upgrade\r\n'
                   'Sec-WebSocket-Version: 13\r\nSec-WebSocket-Key: ' + key + '\r\n\r\n')
        self.sock.sendall(request.encode())
        status = self.file.readline()
        if b' 101 ' not in status:
            raise RuntimeError('WebSocket upgrade failed')
        headers = {}
        while (line := self.file.readline()) != b'\r\n':
            if not line:
                raise RuntimeError('Incomplete handshake')
            name, value = line.decode().split(':', 1)
            headers[name.lower()] = value.strip()
        expected = base64.b64encode(hashlib.sha1(
            (key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
        if headers.get('sec-websocket-accept') != expected:
            raise RuntimeError('Invalid WebSocket handshake')
        assert self.receive()['type'] == 'auth_required'
        self.send({'type': 'auth', 'access_token': os.environ['SUPERVISOR_TOKEN']})
        if self.receive()['type'] != 'auth_ok':
            raise RuntimeError('HA authentication failed')

    def frame(self, opcode, payload):
        mask = os.urandom(4)
        size = len(payload)
        header = bytes([0x80 | opcode])
        if size < 126:
            header += bytes([0x80 | size])
        elif size < 65536:
            header += bytes([0x80 | 126]) + struct.pack('!H', size)
        else:
            header += bytes([0x80 | 127]) + struct.pack('!Q', size)
        self.sock.sendall(header + mask + bytes(v ^ mask[i % 4] for i, v in enumerate(payload)))

    def send(self, value):
        self.frame(1, json.dumps(value).encode())

    def receive(self):
        chunks = bytearray()
        while True:
            header = self.file.read(2)
            if len(header) != 2:
                raise RuntimeError('WebSocket closed')
            flag, length = header
            masked = bool(length & 128)
            length &= 127
            if length == 126:
                length = struct.unpack('!H', self.file.read(2))[0]
            elif length == 127:
                length = struct.unpack('!Q', self.file.read(8))[0]
            if length > 16_000_000:
                raise RuntimeError('Frame too large')
            mask = self.file.read(4) if masked else None
            body = self.file.read(length)
            if mask:
                body = bytes(v ^ mask[i % 4] for i, v in enumerate(body))
            opcode = flag & 15
            if opcode == 8:
                raise RuntimeError('WebSocket closed by server')
            if opcode == 9:
                self.frame(10, body)
                continue
            if opcode == 10:
                continue
            chunks.extend(body)
            if flag & 128:
                return json.loads(chunks)

    def call(self, kind, **data):
        self.counter += 1
        self.send({'id': self.counter, 'type': kind, **data})
        while True:
            response = self.receive()
            if response.get('id') == self.counter:
                if not response.get('success'):
                    raise RuntimeError(json.dumps(response.get('error')))
                return response.get('result')

    def close(self):
        self.frame(8, b'')
        self.file.close()
        self.sock.close()

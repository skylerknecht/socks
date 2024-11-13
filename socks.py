import asyncio
import sys
import socket

class SocksClient:

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    async def negotiate_authentication_method(self) -> bool:
        version, number_of_methods = await self.reader.readexactly(2)
        if version != 5:
            print(f'SOCKS{str(version)} is not supported')
            return False
        methods = []
        for _ in range(number_of_methods):
            method = await self.reader.readexactly(1)
            method = method[0]
            methods.append(method)
        if 0 not in methods:
            disconnect_reply = bytes([
                5,
                int('FF', 16)
            ])
            self.writer.write(disconnect_reply)
            await self.writer.drain()
            return False
        connect_reply = bytes([
            5,
            0
        ])
        self.writer.write(connect_reply)
        await self.writer.drain()
        return True

    async def negotiate_transport(self) -> bool:
        version, cmd, reserved_bit = await self.reader.readexactly(3)
        return cmd == 1  # Only accept CONNECT commands

    async def negotiate_address(self) -> bool:
        self.address_type = int.from_bytes(await self.reader.readexactly(1), byteorder='big')
        print(f"Address Type: {self.address_type}, ", end='')
        if self.address_type == 1:  # IPv4
            self.remote_address = socket.inet_ntoa(await self.reader.readexactly(4))
            self.remote_port = int.from_bytes(await self.reader.readexactly(2), byteorder='big')
            print(f"{self.remote_address}:{self.remote_port}")
            return True

        elif self.address_type == 3:  # FQDN
            fqdn_length = int.from_bytes(await self.reader.readexactly(1), byteorder='big')
            fqdn = await self.reader.readexactly(fqdn_length)
            self.remote_address = fqdn.decode('utf-8')
            self.remote_port = int.from_bytes(await self.reader.readexactly(2), byteorder='big')
            print(f"{self.remote_address}:{self.remote_port}")
            return True

        elif self.address_type == 4:  # IPv6
            self.remote_address = socket.inet_ntop(socket.AF_INET6, await self.reader.readexactly(16))
            self.remote_port = int.from_bytes(await self.reader.readexactly(2), byteorder='big')
            print(f"{self.remote_address}:{self.remote_port}")
            return True
        
        print("Unknown address type.")
        return False

    async def negotiate(self):
        if not await self.negotiate_authentication_method():
            print("Failed during authentication method negotiation.")
            return
        if not await self.negotiate_transport():
            print("Failed during transport negotiation.")
            return
        if not await self.negotiate_address():
            print("Failed during address negotiation.")
            return
        print("Negotiation complete.")

class SocksServer:

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        print("New client connected.")
        client = SocksClient(reader, writer)
        await client.negotiate()

    async def start(self):
        await asyncio.start_server(self.handle_client, self.ip, int(self.port))
        print(f"SOCKS Server running on {self.ip}:{self.port}")
        while True:
            await asyncio.sleep(1)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <ip> <port>")
        sys.exit(1)
    
    ip = sys.argv[1]
    port = sys.argv[2]
    
    socks_server = SocksServer(ip, port)
    try:
        asyncio.run(socks_server.start())
    except KeyboardInterrupt:
        print("Server stopped.")

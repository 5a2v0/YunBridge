from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from select import select
import utils

class Console:
  def __init__(self, port=6571):
    server = socket(AF_INET, SOCK_STREAM)
    server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    utils.try_bind(server, '127.0.0.1', port)
    server.listen(1)  # No connection backlog
    server.setblocking(0)
    self.server = server
    self.clients = [ ]
    self.clients_sendbuffer = { }
    self.sockets = [ server ]
    
    # Data waiting to be transferred to sockets
    self.sendbuffer = ''
    # Data waiting to be transferred to PacketProcessor
    self.recvbuffer = ''
    
  def run(self):
    sockets_to_read_from, sockets_to_write_to, err = select(self.sockets, [], [], 0)
    
    # Accept new connections
    if self.server in sockets_to_read_from:
      self.accept()
      sockets_to_read_from.remove(self.server)
      
    # Read from sockets
    if len(self.sendbuffer) < 1024:
      for sock in sockets_to_read_from:
        self.socket_receive(sock)
    
    # Write buffers to sockets    
    sockets_to_read_from, sockets_to_write_to, err = select([], self.clients, [], 0)
    for client in sockets_to_write_to:
      try:
        buff = self.clients_sendbuffer[client]
        sent = client.send(buff)
        self.clients_sendbuffer[client] = buff[sent:]
      except:
        self.close(client)

    # Drop starving clients
    for client in self.clients:
      if len(self.clients_sendbuffer[client]) > 8192:
        self.close(client)
        
  def socket_receive(self, client):
    chunk = client.recv(1024)
    if chunk == '':
      self.close(client)
      return None
    self.recvbuffer += chunk
        
    # send chunk as echo to all other clients
    for current_client in self.clients:
      if current_client != client:
        self.clients_sendbuffer[current_client] += chunk
            
  def write(self, data):
    # send chunk to all clients
    for c in self.clients:
      self.clients_sendbuffer[c] += data
     
  def read(self, maxlen):
    if maxlen > len(self.recvbuffer):
      res = self.recvbuffer
      self.recvbuffer = ''
    else:
      res = self.recvbuffer[:maxlen]
      self.recvbuffer = self.recvbuffer[maxlen:]
    return res
    
  def available(self):
    return len(self.recvbuffer)
    
  def is_connected(self):
    return len(self.clients) > 0
    
  def accept(self):
    (client, address) = self.server.accept()
    
    # IP filtering could be here
    
    self.sockets.append(client)
    self.clients.append(client)
    self.clients_sendbuffer[client] = ''
    
  def close(self, sock):
    sock.close()
    self.clients.remove(sock)
    self.sockets.remove(sock)
    del self.clients_sendbuffer[sock]
    
console = Console()

class WRITE_Command:
  def run(self, data):
    console.write(data)
    return ''

class READ_Command:
  def run(self, data):
    length = ord(data[0])
    return console.read(length)
    
class CONNECTED_Command:
  def run(self, data):
    if console.is_connected():
      return '\x01'
    else:
      return '\x00'
      
def init(command_processor):
  command_processor.register('P', WRITE_Command())
  command_processor.register('p', READ_Command())
  command_processor.register('a', CONNECTED_Command())
  command_processor.register_runner(console)

def test():
  while True:
    console.process(1)
    
if __name__ == '__main__':
  test()

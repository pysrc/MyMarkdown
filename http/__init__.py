import socket
import os
import hashlib
import threading
import time
from urllib import parse


def response(body: bytes, headers={}):
    res = b'''HTTP/1.1 200 OK'''
    for k in headers:
        res += (b'\n' + k + b': ' + headers[k])
    return res + b'\n\n' + body


class Request:
    def __init__(self, content: bytes):
        self.content = content.replace(b'\r', b'')
        lines = self.content.split(b'\n')
        r0 = lines[0].split(b' ')
        self.method = r0[0]
        pt = r0[1].split(b'?')
        self.path = pt[0]
        self.pathdata = b'' if len(pt) == 1 else pt[1]
        self.version = r0[2]

        self.headers = {}
        for x in range(1, len(lines)):
            if lines[x] == b'':
                break
            i = lines[x].find(b':')
            if i != -1:
                self.headers[lines[x][:i]] = lines[x][i + 1:].lstrip(b' ')
        split = self.content.find(b'\n\n')
        if split != -1:
            self.body = self.content[split + 2:]
        else:
            self.body = b''


class Handle:
    def __init__(self):
        pass

    def handle(self, soc: socket.socket):
        body = b'OK!'
        headers = {}
        headers[b'Content-Type'] = b'text/html; charset=UTF-8'
        res = response(body, headers)
        soc.send(res)
        soc.close()


class HttpServer:
    def __init__(self, host: str, port: int):
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.soc.bind((host, port))
        self.handle = Handle()

    def setHandle(self, handle: Handle):
        self.handle = handle

    def run(self):
        self.soc.listen(10)
        while True:
            client, addr = self.soc.accept()
            threading.Thread(target=self.handle.handle, args=(client,)).start()


class MyHandle(Handle):
    def __init__(self, scans=[]):
        # 静态资源目录
        self.scans = scans
        self.scans.append(os.path.dirname(os.path.realpath(__file__)))
        self.content = b''
        self.title = b'Markdown'
        self.md5 = hashlib.md5(self.content).hexdigest().encode("utf-8")

    def getResources(self, relativePath):
        # 获取服务器资源（静态文件）
        for i in self.scans:
            pth = i + relativePath
            if os.path.isfile(pth):
                f = open(pth, 'rb')
                res = f.read()
                f.close()
                return res
        return b''

    def handle(self, soc: socket.socket):
        data = soc.recv(1048576)
        request = Request(data)
        res = b''
        if request.path == b'/sse':
            # sse protocol
            headers = {
                b'Content-Type': b'text/event-stream',
                b'Cache-Control': b'no-cache',
                b'Connection': b'keep-alive',
                b'Access-Control-Allow-Origin': b'*',
            }
            head = response(b'', headers)
            soc.send(head)
            while True:
                soc.send(b'data: ' + self.md5 + b'\n\n')
                time.sleep(1)
            soc.close()
            return
        elif request.path == b'/pmd':
            # push markdown
            self.content = request.body
            pd = parse.unquote(request.pathdata.decode("utf-8"))
            pt = os.path.dirname(pd[5:])
            self.title = os.path.basename(pd[5:]).encode("utf-8")
            self.scans.append(pt)
            self.md5 = hashlib.md5(self.content).hexdigest().encode("utf-8")
            res = response(b'OK')
        elif request.path == b'/title':
            res = response(self.title)
        elif request.path == b'/gmd':
            # get markdown
            res = response(self.content)
        elif request.path == b'/':
            body = self.getResources("/index.html")
            res = response(
                body, {b'Content-Type': b'text/html; charset=UTF-8'})
        else:
            res = response(self.getResources(
                parse.unquote(request.path.decode("utf-8"))))
        soc.send(res)
        soc.close()


if __name__ == '__main__':
    handle = MyHandle()
    server = HttpServer('0.0.0.0', 80)
    server.setHandle(handle)
    server.run()

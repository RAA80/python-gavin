"""
Minimalistic motion-JPEG-over-HTTP server
-----------------------------------------

Requirements:
    - python 2.7 or 3.x;
    - for numpy.array frame format: PIL or cv2;
    - for QImage frame format: PyQt4 or PyQt5.

Example of usage:

    import minimjpeg
    ...
    frame1 = acquire_new_frame_from_source()
    minimjpeg.handle_frame(frame1, channel='', port=80, max_quality=80, min_delay=0.040, ip='', debug=False)  # send frame for all clients of given server
    frame2 = acquire_new_frame_from_another_source()
    minimjpeg.handle_frame(frame2, channel='', port=81, max_quality=80, min_delay=0.040, ip='', debug=False)  # send frame for all clients of another server
    ...
    # here open any browser using URL `http://<ip>:<port>/?channel=<channel>&quality=<1..100>&delay=<0..1000>`
    # all URL parameters can be omitted (default channel is '', default quality is max_quality, default delay is min_delay)
    ...
    minimjpeg.handle_frame(None, port=80, ip='')  # gracefully close connections of given server
    minimjpeg.handle_frame(None, port=81, ip='')  # gracefully close connections of another server

That's all!
"""

import socket
import select
import traceback
import threading
import re
import time

if hasattr(time, 'monotonic'):
    timer = time.monotonic
else:
    timer = time.time


"""
Structure of SERVER disctionary:
    {
        (<ip>, <port>): (
            <lock>,
            <server_socket>,
            {
                <channel>: <last_time>,
                ...
            },
            {
                <remode_addr>: (
                    <client_socket>,
                    <channel>,
                    <quality>,
                    <delay>,
                    <last_sent>
                ),
                ...
            }
        ),
        ...
    }
"""
SERVERS, SERVERS_LOCK = {}, threading.Lock()
BOUNDARY = b"mjpegboundary"
GET_RE = re.compile(r"GET /(\S*)")
PARAM_RE = re.compile(r"([0-9a-zA-Z_]+)=([0-9a-zA-Z_]+)")

STREAM_HEADER = (
    "HTTP/1.0 200 OK\r\n"
    "Connection: close\r\n"
    "Content-Type: multipart/x-mixed-replace;boundary={}\r\n"
    "\r\n".format(BOUNDARY).encode()
)


try:
    try:
        from PyQt5.Qt import QImage, QBuffer
    except ImportError:
        from PyQt4.Qt import QImage, QBuffer
    def _jpeg_compress_qimage(im, quality):
        buf = QBuffer()
        im.save(buf, "JPEG", quality)
        return buf.data()
except ImportError:
    QImage = None
    def _jpeg_compress_qimage(im, quality):
        raise Exception("No backend for QImage frame format")

try:
    import PIL
    import PIL.Image
    import io
    if hasattr(PIL, "__version__"):  # not so old
        BytesIO = io.BytesIO
    else:  # like Astra SE 1.3
        class BytesIO(io.BytesIO):
            def fileno(self):
                raise AttributeError()
    def _jpeg_compress_numpy(im, quality):
        buf = BytesIO()
        PIL.Image.fromarray(im).save(buf, 'JPEG', quality=quality)
        return buf.getvalue()
except ImportError:
    try:
        import cv2
        def _jpeg_compress_numpy(im, quality):
            ret, buf = cv2.imencode('*.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, quality])
            return bytearray(buf)
    except ImportError:
        def _jpeg_compress_numpy(im, quality):
            raise Exception("No backend for numpy frame format")


def _jpeg_compress(im, quality):
    if type(im) == QImage:
        return _jpeg_compress_qimage(im, quality)
    return _jpeg_compress_numpy(im, quality)


def handle_frame(frame, channel='', ip='', port=8080,
        min_delay=0.010, default_delay=0.040,
        max_quality=95, default_quality=80,
        default_chan='',
        headers={}, debug=False, sendall=False):
    global SERVERS, SERVERS_LOCK
    ret, sent = [], 0
    lock = None
    SERVERS_LOCK.acquire()
    try:
        now = timer()
        local_address = (ip, port)
        #SERVERS_LOCK.acquire()
        if local_address not in SERVERS:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(local_address)
            server.listen(5)
            lock = threading.Lock()
            SERVERS[local_address] = (lock, server, {}, {})
        SERVERS[local_address][0].acquire()
        #SERVERS_LOCK.release()
        lock, server, last_times, clients = SERVERS[local_address]
        if channel not in last_times:
            last_times[channel] = now - 1.0
        if frame is None:
            for (sock, _, _, _, _) in clients.values():
                sock.close()
            server.close()
            lock.release()
            #SERVERS_LOCK.acquire()
            del SERVERS[local_address]
            SERVERS_LOCK.release()
            return ret, sent
        r, _, _ = select.select([server], [], [], 0.0)
        if server in r:
            sock, remote_address = server.accept()
            if debug:
                print("New MJPEG connection from %s" % (remote_address,))
            clients[remote_address] = (sock, default_chan, default_quality, default_delay, 0.0, False)
        if len(clients) == 0:
            lock.release()
            SERVERS_LOCK.release()
            return ret, sent
        ret = list(clients.keys())
        r, _, _ = select.select([s for (s, _, _, _, _, _) in clients.values()], [], [], 0.0)
        for addr, (sock, chan, quality, delay, last_sent, headers_sent) in list(clients.items()):
            if sock in r:
                try:
                    data = sock.recv(1500).decode()
                    if len(data) == 0:
                        raise Exception("Connection closed by client")
                    paths = GET_RE.findall(data)
                    if debug:
                        print("Paths [req %s byte(s)] from %s: %s" % (len(data), addr, paths))
                    if 'index.html' in paths or ('' in paths and default_chan is None):
                        getattr(sock, 'sendall' if sendall else 'send')(
                            "HTTP/1.0 200 OK\r\n"
                            "Connection: close\r\n"
                            "Content-Type: text/html\r\n\r\n"
                            "<html><head><title>Motion JPEG over HTTP</title></head><body>" +
                            "".join(['<li><a href="/?channel={name}">Channel {i} [{name}]</a>'.format(i=i, name=name)
                                for i, name in enumerate(sorted(last_times.keys()))]) +
                            "</body></html>\r\n"
                        )
                        sock.close()
                        del clients[addr]
                        continue
                    params = dict(PARAM_RE.findall(data))
                    quality = min(max_quality, int(params.get('quality', quality)))
                    delay = max(min_delay, float(params.get('delay', delay)) * 1e-3)
                    chan = params.get('channel', params.get('source', chan))
                    clients[addr] = (sock, chan, quality, delay, last_sent, True)
                    if debug:
                        print("Sending headers to %s" % (addr,))
                    getattr(sock, 'sendall' if sendall else 'send')(
                        STREAM_HEADER
                    )
                    sent += len(STREAM_HEADER)
                except Exception:
                    del clients[addr]
        receivers = [(a, (s, c, q, d, t, hs)) for (a, (s, c, q, d, t, hs)) in list(clients.items()) 
                     if hs and c == channel and now - t >= d]
        if len(receivers) == 0 or now - last_times[channel] < min_delay:
            lock.release()
            SERVERS_LOCK.release()
            return ret, sent
        sheaders = "".join(["{}: {}\r\n".format(k, v) for (k, v) in headers.items()])
        frame_jpeg = _jpeg_compress(frame, max([q for (a, (_, _, q, _, _, _)) in receivers]))
        frame_data = (
            "--{}\r\n"
            "Content-Type: image/jpeg\r\n"
            "Content-Length: {}\r\n"
            "Cache-Control: no-cache\r\n"
            "{}"
            "\r\n".format(BOUNDARY, len(frame_jpeg), sheaders).encode()
        ) + frame_jpeg
        for addr, (sock, chan, quality, delay, last_sent, headers_sent) in receivers:
            try:
                if debug:
                    print("Sending frame to %s" % (addr,))
                getattr(sock, 'sendall' if sendall else 'send')(
                    frame_data
                )
                sent += len(frame_data)
                clients[addr] = (sock, chan, quality, delay, now, headers_sent)
            except Exception:
                if debug:
                    traceback.print_exc()
                del clients[addr]
        last_times[channel] = now
    except Exception as ex:
        if debug:
            traceback.print_exc()
    if lock is not None:
        lock.release()
    SERVERS_LOCK.release()
    return ret, sent

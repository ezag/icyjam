import sys

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.python import usage
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET, Site

class Shoutcast(Protocol):
    MEDIA, METADATA_SIZE, METADATA = range(1, 4)

    def __init__(self, metaint):
        self.metaint = metaint
        self.media_bytes_remaining = self.metaint
        self.state = self.MEDIA
        self.buffer_ = ''

    def dataReceived(self, chunk):
        self.buffer_ += chunk
        if self.state == self.MEDIA:
            media = self.buffer_[:self.media_bytes_remaining]
            self.buffer_ = self.buffer_[self.media_bytes_remaining:]
            self.mediaReceived(media)
            self.media_bytes_remaining -= len(media)
            if self.media_bytes_remaining == 0:
                self.state = self.METADATA_SIZE
        if self.state == self.METADATA_SIZE:
            if len(self.buffer_) > 0:
                self.metadata_bytes_remaining = ord(self.buffer_[0]) * 16
                self.buffer_ = self.buffer_[1:]
                self.metadata = ''
                self.state = self.METADATA
            else:
                pass
        if self.state == self.METADATA:
            metadata_part = self.buffer_[:self.metadata_bytes_remaining]
            self.buffer_ = self.buffer_[self.metadata_bytes_remaining:]
            self.metadata += metadata_part
            self.metadata_bytes_remaining -= len(metadata_part)
            if self.metadata_bytes_remaining == 0:
                self.metadataReceived(self.parseMetadata(self.metadata), self.metadata)
                self.media_bytes_remaining = self.metaint
                self.state = self.MEDIA

    @staticmethod
    def parseMetadata(raw_metadata):
        return dict(
            (k, v[1:-1] if v[0] in ("'", '"') and v[0] == v[-1] else v)
            for k, v in (
                kv.split('=', 1)
                for kv in raw_metadata.rstrip('\x00').split(';') if kv))

    def mediaReceived(self, chunk):
        pass

    def metadataReceived(self, headers, raw_metadata):
        pass


class ShoutcastJammer(Shoutcast):
    def __init__(self, *args, **kwargs):
        self.cb_media = kwargs.pop('cb_media')
        Shoutcast.__init__(self, *args, **kwargs)

    def mediaReceived(self, chunk):
        print 'received {} bytes'.format(len(chunk))
        self.cb_media(chunk)

    def metadataReceived(self, headers, raw_metadata):
        print 'metadata {}'.format(headers)
        self.cb_media(chr(len(raw_metadata)))
        self.cb_media(raw_metadata)


class JammedStream(Resource):
    isLeaf = True

    def render_GET(self, request):
        print request.uri
        self.r = request
        url = request.uri.lstrip('/')
        request.responseHeaders = Headers({
            'Content-Type': ['audio/mpeg'],
            'icy-metaint': ['8192'],
        })
        agent = Agent(reactor)
        d = agent.request('GET', url, Headers({'Icy-MetaData': ['1']}))
        d.addCallback(self.cbRequest)
        d.addBoth(self.cbShutdown)
        return NOT_DONE_YET

    def cbRequest(self, response):
        metaint = int(response.headers.getRawHeaders('Icy-Metaint')[0])
        response.deliverBody(ShoutcastJammer(metaint, cb_media=self.cbMedia))
        return Deferred()

    def cbShutdown(self, request):
        print request.printTraceback()

    def cbMedia(self, chunk):
        self.r.write(chunk)


class Options(usage.Options):
    optParameters = (
        ('port', 'p', 5000, 'Port to listen', int),
    )


if __name__ == '__main__':
    config = Options()
    try:
        config.parseOptions()
    except usage.UsageError, errortext:
        print '%s: %s' % (sys.argv[0], errortext)
        print '%s: Try --help for usage details.' % (sys.argv[0])
        sys.exit(1)
    reactor.listenTCP(config['port'], Site(JammedStream()))
    reactor.run()

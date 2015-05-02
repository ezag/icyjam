import sys

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent
from twisted.web.http_headers import Headers

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
                self.metadataReceived(self.parseMetadata(self.metadata))
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

    def metadataReceived(self, headers):
        pass


class ShoutcastJammer(Shoutcast):
    def mediaReceived(self, chunk):
        sys.stdout.write(chunk)


if __name__ == '__main__':
    agent = Agent(reactor)
    d = agent.request(
        'GET',
        sys.argv[1],
        Headers({'Icy-MetaData': ['1']}),
    )

    def cbRequest(response):
        metaint = int(response.headers.getRawHeaders('Icy-Metaint')[0])
        response.deliverBody(ShoutcastJammer(metaint))
        return Deferred()
    d.addCallback(cbRequest)

    def cbShutdown(ignored):
        reactor.stop()
    d.addBoth(cbShutdown)

    reactor.run()

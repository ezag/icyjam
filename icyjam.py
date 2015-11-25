import argparse
import asyncio

from aiohttp import web

class ArgumentParser(argparse.ArgumentParser):
    def __init__(self):
        super(ArgumentParser, self).__init__()
        self.add_argument('--port', default=8080, type=int)

async def handle(request):
    return web.Response(body='Hello World'.encode('utf-8'))

async def init(loop, host, port):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handle)
    srv = await loop.create_server( app.make_handler(), host, port)
    print('Server started at http://{}:{}/'.format(host, port))
    return srv

if __name__ == '__main__':
    args = ArgumentParser().parse_args()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop, 'localhost', args.port))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

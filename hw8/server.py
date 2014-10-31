from json import dumps, load
from platform import node
from socket import gethostbyname, gethostname
from urllib2 import urlopen

from klein import Klein

from hw8 import __version__


class SimpleApp(object):
    app = Klein()
    number = 0

    @app.route('/')
    def status(self, request):
        request.setHeader('Content-Type', 'application/json')

        self.number += 1
        return dumps({
            'request_number': self.number,
            'ip': {
                'private': gethostbyname(gethostname()),
                'public': load(urlopen('http://httpbin.org/ip'))['origin']
            }, 'version': __version__, 'host': node()
        })


if __name__ == '__main__':
    simple_app = SimpleApp()
    simple_app.app.run('0.0.0.0', 8080)

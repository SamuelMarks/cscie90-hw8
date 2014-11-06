from json import dumps, load
from platform import node
from socket import gethostbyname, gethostname
from urllib2 import urlopen

from klein import Klein

from __init__ import __version__
from SQSWrapper import SQSWrapper


class SimpleApp(object):
    app = Klein()
    number = 0
    last_response = {}

    def __init__(self, sqs_obj):
        self.sqs = sqs_obj

    @app.route('/')
    def status(self, request):
        request.setHeader('Content-Type', 'application/json')

        self.number += 1
        self.last_response = {
            'request_number': self.number,
            'ip': {
                'private': gethostbyname(gethostname()),
                'public': load(urlopen('http://httpbin.org/ip'))['origin']
            }, 'version': __version__, 'host': node()
        }
        return dumps(self.last_response)

    @app.route('/msg/send')  # No need to expose POST/PUT/PATCH, just send through the last response ^
    def msg_send(self, request):
        request.setHeader('Content-Type', 'application/json')
        self.sqs.send_message(self.last_response)
        return dumps(dict(sent=self.last_response))

    @app.route('/msg/receive')
    def msg_receive(self, request):
        request.setHeader('Content-Type', 'application/json')
        return dumps(dict(received=map(lambda m: m.get_body(), self.sqs.receive_message(number_messages=2))))


if __name__ == '__main__':
    SimpleApp(None).app.run('0.0.0.0', 8080)
    '''
    my_queue_name = 'cscie90_hw8'
    with SQSWrapper(queue_name=my_queue_name, persist=False) as sqs:
        if not sqs.create_queue():
            sqs.get_queue()  # Assume it's been created already and just get it
        sqs.send_message('Hello world')
        sqs.send_message('Goodbye world')
        print 'Retrieved from queue:', map(lambda m: m.get_body(), sqs.receive_message(number_messages=2))

        simple_app = SimpleApp(sqs)
        simple_app.app.run('0.0.0.0', 8080)
    '''

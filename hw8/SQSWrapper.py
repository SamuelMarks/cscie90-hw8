#!/usr/bin/env python

from os.path import expanduser, join as path_join
from random import randint

from boto.sqs import connect_to_region
from boto.exception import SQSError


def print_then_false(s):
    print s
    return False


def print_then_raise(s, e):
    print "s = {0}...".format(s)
    raise e


find_and_return_str = lambda s, k: s[s.rfind(k):len(s)]


class SQSWrapper(object):
    aws_keys = {i[0].rstrip(): i[1].lstrip()
                for i in tuple(e.rstrip('\n').split('=') for e in
                               open(path_join(expanduser('~'), '.aws', 'credentials')).readlines()[1:])}
    queue = None

    def __init__(self, queue_name, random_rename=True, persist=False):
        self.queue_name = queue_name
        if random_rename:  # To handle 'You must wait 60 seconds after deleting a queue' error
            self.queue_name += str(randint(1, 100))
        self.conn = self.configure()
        self.persist = persist

    def __enter__(self):
        return self

    def __exit__(self, ext, exv, trb):
        if not self.persist:
            self.delete()

    def configure(self, region='ap-southeast-2'):
        self.conn = connect_to_region(**dict(region_name=region, **self.aws_keys))
        return self.conn  # Hmm, if only I could inherit a class from this connection

    def create_queue(self, visibility_timeout=20):
        try:
            self.queue = self.conn.create_queue(self.queue_name, visibility_timeout)
            return True
        except SQSError as e:
            error = str(e)
            # error = ElementTree.fromstring(err[err.find('<?xml'):])
            # Why parse [O(n log n) or O(n) at best], then find [O(1) or O(log n) or O(n)]
            # Whereas skipping the parsing step and with a constant number
            # of options, it will only be: [O(1) * n + o(1)]
            # If I get the time I will implement the Aho-Corasick string matching algorithm

            delay_error = 'You must wait 60 seconds after deleting a queue ' \
                          'before you can create another with the same name.'
            unavailable = 'The requested queue name is not available.'
            unavailable_q = unavailable.replace(' name', ': "{0}"'.format(self.queue_name))
            no_queue = 'No queue to remove'
            # print 'error =', error

            if not error:
                raise e
            return {
                find_and_return_str(error, unavailable_q): print_then_false(unavailable_q),
                find_and_return_str(error, delay_error): print_then_false(delay_error),
                find_and_return_str(error, no_queue): print_then_false(no_queue)
            }.get(unavailable, self.get_queue_and_return_true())

    def get_queue_and_return_true(self):
        self.get_queue()
        return True

    def get_queue(self):
        self.queue = self.conn.get_queue(self.queue_name)
        return self.queue

    def get_queue_attributes(self, attribute='All'):
        return self.conn.get_queue_attributes(queue=self.queue, attribute=attribute)

    def send_message(self, message_content, delay_seconds=None,
                     message_attributes=None):
        queue = self.queue
        # l.copy(locals()); l.pop('self')

        if not queue:
            print "queue =", queue
        else:
            return self.conn.send_message(**{k: v for k, v in locals().iteritems() if k != 'self'})

    def receive_message(self, number_messages=1, visibility_timeout=None,
                        attributes=None, wait_time_seconds=None, message_attributes=None):
        queue = self.queue
        messages = self.conn.receive_message(**{k: v for k, v in locals().iteritems() if k != 'self'})
        # return map(lambda m: m.get_body(), messages)
        return messages

    def delete_message(self, message):
        return self.conn.delete_message(self.queue, message)

    def delete(self):
        if not self.queue:
            print "No queue to remove"
            return []
        return self.conn.delete_queue(self.queue)


if __name__ == '__main__':
    my_queue_name = 'cscie90_hw6_throwaway'
    with SQSWrapper(queue_name=my_queue_name, persist=False) as sqs:
        if not sqs.create_queue():
            sqs.get_queue()  # Assume it's been created already and just get it
        sqs.send_message('Hello world')
        sqs.send_message('Goodbye world')
        print 'Retrieved from queue:', map(lambda m: m.get_body(), sqs.receive_message(number_messages=2))
        # Unlike SimpleDB this doesn't have consistent read, so ^ will
        # return any(['Hello World'], ['Goodbye World'], ['Hello World', 'Goodbye World'])
        # I could send batch messages I suppose...

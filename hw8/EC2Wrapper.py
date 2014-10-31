#!/usr/bin/env python

from os.path import expanduser, join as path_join
from random import randint
from pprint import PrettyPrinter

from boto.ec2 import connect_to_region
from boto.exception import EC2ResponseError


pp = PrettyPrinter(indent=4).pprint


def print_then_false(s):
    print s
    return False


def print_then_raise(s, e):
    print "s = {0}...".format(s)
    raise e


find_and_return_str = lambda s, k: s[s.rfind(k):len(s)]


class EC2Wrapper(object):
    aws_keys = {i[0].rstrip(): i[1].lstrip()
                for i in tuple(e.rstrip('\n').split('=') for e in
                               open(path_join(expanduser('~'), '.aws', 'credentials')).readlines()[1:])}
    instance = None

    def __init__(self, ami_image_id, random_rename=False, persist=False):
        self.instance_name = ami_image_id
        if random_rename:  # To handle 'You must wait 60 seconds after deleting a instance' error
            self.instance_name += str(randint(1, 100))
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

    def list_all_images(self, filters=None):
        if not filters:  # Not as default arguments, as they should be immutable
            filters = {
                'architecture': 'x86_64',
                'name': 'ubuntu/images/ebs-ssd/ubuntu-trusty-14.04-amd64-server-20140927',

            }
        return self.conn.get_all_images(owners=['amazon'], filters=filters)

    def create_instance(self, visibility_timeout=20):
        try:
            self.instance = self.conn.create_instance(self.instance_name, visibility_timeout)
            return True
        except EC2Error as e:
            error = str(e)
            # error = ElementTree.fromstring(err[err.find('<?xml'):])
            # Why parse [O(n log n) or O(n) at best], then find [O(1) or O(log n) or O(n)]
            # Whereas skipping the parsing step and with a constant number
            # of options, it will only be: [O(1) * n + o(1)]
            # If I get the time I will implement the Aho-Corasick string matching algorithm

            delay_error = 'You must wait 60 seconds after deleting a instance ' \
                          'before you can create another with the same name.'
            unavailable = 'The requested instance name is not available.'
            unavailable_q = unavailable.replace(' name', ': "{0}"'.format(self.instance_name))
            no_instance = 'No instance to remove'
            # print 'error =', error

            if not error:
                raise e
            return {
                find_and_return_str(error, unavailable_q): print_then_false(unavailable_q),
                find_and_return_str(error, delay_error): print_then_false(delay_error),
                find_and_return_str(error, no_instance): print_then_false(no_instance)
            }.get(unavailable, self.get_instance_and_return_true())

    def get_instance_and_return_true(self):
        self.get_instance()
        return True

    def get_instance(self):
        self.instance = self.conn.get_instance(self.instance_name)
        return self.instance

    def get_instance_attributes(self, attribute='All'):
        return self.conn.get_instance_attributes(instance=self.instance, attribute=attribute)

    def send_message(self, message_content, delay_seconds=None,
                     message_attributes=None):
        instance = self.instance
        # l.copy(locals()); l.pop('self')

        if not instance:
            print "instance =", instance
        else:
            return self.conn.send_message(**{k: v for k, v in locals().iteritems() if k != 'self'})

    def receive_message(self, number_messages=1, visibility_timeout=None,
                        attributes=None, wait_time_seconds=None, message_attributes=None):
        instance = self.instance
        messages = self.conn.receive_message(**{k: v for k, v in locals().iteritems() if k != 'self'})
        # return map(lambda m: m.get_body(), messages)
        return messages

    def delete_message(self, message):
        return self.conn.delete_message(self.instance, message)

    def delete(self):
        if not self.instance:
            print "No instance to remove"
            return []
        return self.conn.delete_instance(self.instance)


if __name__ == '__main__':
    my_instance_name = 'cscie90_hw6_throwaway'
    with EC2Wrapper(ami_image_id=my_instance_name, persist=False) as ec2:
        for image in ec2.list_all_images():
            print 'name =', image.name
            print 'tags =', image.tags
            print 'description =', image.description
            print 'type =', image.type
            print 'architecture =', image.architecture

        print tuple(image for image in ec2.list_all_images()
                    if '14.04' in image.name)
        # pp(dir(ec2.list_all_images()[0]))
        #if not ec2.create_instance():
        #ec2.get_instance()  # Assume it's been created already and just get it
        #ec2.send_message('Hello world')
        #ec2.send_message('Goodbye world')
        #print 'Retrieved from instance:', map(lambda m: m.get_body(), ec2.receive_message(number_messages=2))
        # Unlike SimpleDB this doesn't have consistent read, so ^ will
        # return any(['Hello World'], ['Goodbye World'], ['Hello World', 'Goodbye World'])
        # I could send batch messages I suppose...

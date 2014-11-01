#!/usr/bin/env python

# TODO: Implement this, ran out of time so did it through the management console web frontend

from os.path import expanduser, join as path_join
from sys import stderr
from random import randint
from pprint import PrettyPrinter

from boto.ec2.elb import connect_to_region

pp = PrettyPrinter(indent=4).pprint


class ELBWrapper(object):
    aws_keys = {i[0].rstrip(): i[1].lstrip()
                for i in tuple(e.rstrip('\n').split('=') for e in
                               open(path_join(expanduser('~'), '.aws', 'credentials')).readlines()[1:])}
    instance = None
    image_id = None

    def __init__(self, ami_image_id, name='', random_rename=False, persist=False):
        self.ami_image_id = ami_image_id
        self.instance_name = name
        if random_rename:  # To handle 'You must wait 60 seconds after deleting a instance' error
            self.instance_name += str(randint(1, 100))
        self.conn = self.configure()
        self.persist = persist

    def __enter__(self):
        if self.instance:
            self.start_instance()
        else:
            print >> stderr, 'Warning: No instance instantiated'
        return self

    def __exit__(self, ext, exv, trb):
        if not self.persist:
            self.delete()

    def configure(self, region='ap-southeast-2'):
        self.conn = connect_to_region(region_name=region, **self.aws_keys)
        return self.conn  # Hmm, if only I could inherit a class from this connection


if __name__ == '__main__':
    with ELBWrapper('') as elb:
        print tuple(group for group in elb.list_security_groups() if group.name == 'ssh_http_rdp')[0]
        # print filter(lambda elem: dir(elem), elb.list_security_groups())[0]

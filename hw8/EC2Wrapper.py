#!/usr/bin/env python

# TODO: Until I can work out how to search for an AMI by name, this module is pretty much useless

from os.path import expanduser, join as path_join
from random import randint
from pprint import PrettyPrinter

from boto.ec2 import connect_to_region
from boto.manage.cmdshell import sshclient_from_instance
from boto.exception import EC2ResponseError

from fabric.tasks import execute

pp = PrettyPrinter(indent=4).pprint


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
                'architecture': 'x86_64'

            }
        return self.conn.get_all_images(owners=['amazon'], filters=filters)

    def create_instance(self, visibility_timeout=20):
        self.instance = self.conn.create_instance(self.instance_name, visibility_timeout)
        return True

    def get_instances(self):
        return self.conn.get_all_instances(filters={'architecture': 'x86_64'})

    def get_instance(self):
        self.instance = self.conn.get_instance(self.instance_name)
        return self.instance

    def get_instance_attributes(self, attribute='All'):
        return self.conn.get_instance_attributes(instance=self.instance, attribute=attribute)

    def delete(self):
        if not self.instance:
            print "No instance to remove"
            return []
        return self.conn.delete_instance(self.instance)

    @staticmethod
    def run(inst, commands, username='ubuntu'):
        """
        Returns a tuple of tuples consisting of:
        #    The integer status of the command
        #    A string containing the output of the command
        #    A string containing the stderr output of the command
        """
        ssh_client = sshclient_from_instance(inst, user_name=username,
                                             ssh_key_file=expanduser(path_join(expanduser('~'),
                                                                               '.ssh', 'aws', 'private',
                                                                               'cscie90.pem')))
        return tuple(ssh_client.run(command) for command in commands)

    @staticmethod
    def run2(commands, host):
        return execute(commands, host=host)

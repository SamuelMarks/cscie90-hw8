#!/usr/bin/env python

from os.path import expanduser, join as path_join
from sys import stderr
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
    image_id = None

    def __init__(self, ami_image_id, random_rename=False, persist=False):
        self.instance_name = ami_image_id
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

    def list_all_images(self, filters=None):
        if not filters:  # Not as default arguments, as they should be immutable
            filters = {
                'architecture': 'x86_64'
                # TODO: Figure out how to search for an AMI by name
            }
        return self.conn.get_all_images(owners=['amazon'], filters=filters)

    def create_image_from_instance(self, name, description=None, instance_id=None):
        if not instance_id:
            instance_id = self.instance.id
        self.image_id = self.conn.create_image(instance_id, name, description)
        return self.image_id

    def get_instances(self):
        return self.conn.get_all_instances(filters={'architecture': 'x86_64'})

    def set_instance(self, instance):  # Eww, Java-style method
        self.instance = instance
        return self.instance

    def start_instance(self, instance_id=None):
        if not instance_id:
            instance_id = self.instance.id
        self.conn.start_instances(instance_id)
        self.instance = self.conn.start_instances(instance_id)[0]
        return self.instance

    def delete(self):
        if not self.instance:
            print "No instance to remove"
            return []
        return self.conn.stop_instances(self.instance.id)  # Stop, don't delete (for now)

    @staticmethod
    def run(inst, commands, username='ubuntu'):
        """
        Uses boto to figure out how to SSH in and run commands

        :return a tuple of tuples consisting of:
        #    The integer status of the command
        #    A string containing the output of the command
        #    A string containing the stderr output of the command
        """
        ssh_client = sshclient_from_instance(inst, user_name=username,
                                             ssh_key_file=path_join(expanduser('~'), '.ssh', 'aws',
                                                                    'private', 'cscie90.pem'))
        return tuple(ssh_client.run(command) for command in commands)

    @staticmethod
    def run2(commands, host):
        """
        Uses Fabric to execute commands over SSH

        :param commands: callable with one or more usages of run/sudo/cd
        :param host: DNS name or IP address
        """
        return execute(commands, host=host)

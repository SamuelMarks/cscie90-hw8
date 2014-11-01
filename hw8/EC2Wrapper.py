#!/usr/bin/env python

from os.path import expanduser, join as path_join
from random import randint
from pprint import PrettyPrinter
from functools import partial

from boto.ec2 import connect_to_region
from boto.manage.cmdshell import sshclient_from_instance
from boto.exception import EC2ResponseError

from fabric.tasks import execute
from fabric.api import env as fabric_env, sudo
from fabric.context_managers import cd
from fabric.contrib.files import exists

pp = PrettyPrinter(indent=4).pprint

fabric_env.skip_bad_hosts = True
fabric_env.user = 'ubuntu'
fabric_env.sudo_user = 'ubuntu'
fabric_env.key_filename = expanduser(path_join(expanduser('~'), '.ssh', 'aws', 'private', 'cscie90.pem'))


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
                'architecture': 'x86_64'

            }
        return self.conn.get_all_images(owners=['amazon'], filters=filters)

    def get_instances(self):
        return self.conn.get_all_instances(filters={'architecture': 'x86_64'})

    def create_instance(self, visibility_timeout=20):
        try:
            self.instance = self.conn.create_instance(self.instance_name, visibility_timeout)
            return True
        except EC2ResponseError as e:
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


def first_run():
    fabric_env.sudo_user = 'root'
    if exists('"$HOME/cscie90-hw8"', use_sudo=True):
        return deploy()

    sudo('apt-get update')
    sudo('apt-get install -q -y --force-yes python-pip python-twisted git')
    sudo('git clone https://github.com/SamuelMarks/cscie90-hw8', user='ubuntu')
    sudo('pip install -r ~/cscie90-hw8/requirements.txt')


def deploy():
    if not exists('"$HOME"/cscie90-hw8', use_sudo=True):
        return first_run()
    with cd('"$HOME/cscie90-hw8"'):
        sudo('git pull', user='ubuntu')


def serve():
    with cd('"$HOME/cscie90-hw8/hw8"'):
        sudo('python server.py', user='ubuntu')


if __name__ == '__main__':
    my_instance_name = 'cscie90_hw8_throwaway'
    with EC2Wrapper(ami_image_id=my_instance_name, persist=False) as ec2:
        hw8_instances = tuple(inst for res in ec2.get_instances() for inst in res.instances
                              if inst.tags.get('Name', '').startswith('hw8'))
        for instance in hw8_instances:
            run3 = partial(ec2.run2, host=getattr(instance, 'public_dns_name'))
            # print run3(lambda: sudo('whoami'))
            print run3(first_run)
            print run3(deploy)
            print run3(serve)
            '''
            for i in dir(instance):
                if not i.startswith('_'):
                    print i, '=', getattr(instance, i)
            '''
        '''
        for instance in ec2.get_instances():
            for i in dir(instance.instances):
                if not i.startswith('_'):
                    print i, '=', getattr(instance.instances, i)
        '''
        '''
        for image in ec2.list_all_images():
            print 'name =', image.name
            print 'tags =', image.tags
            print 'description =', image.description
            print 'type =', image.type
            print 'architecture =', image.architecture

        print tuple(image for image in ec2.list_all_images()
                    if '14.04' in image.name)
        '''
        # pp(dir(ec2.list_all_images()[0]))
        # if not ec2.create_instance():
        # ec2.get_instance()  # Assume it's been created already and just get it
        # ec2.send_message('Hello world')
        # ec2.send_message('Goodbye world')
        # print 'Retrieved from instance:', map(lambda m: m.get_body(), ec2.receive_message(number_messages=2))
        # Unlike SimpleDB this doesn't have consistent read, so ^ will
        # return any(['Hello World'], ['Goodbye World'], ['Hello World', 'Goodbye World'])
        # I could send batch messages I suppose...

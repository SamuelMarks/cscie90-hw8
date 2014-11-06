from os.path import expanduser, join as path_join
from functools import partial
from time import sleep
from exceptions import BaseException

from fabric.context_managers import cd
from fabric.contrib.files import exists
from fabric.api import env as fabric_env, sudo

from EC2Wrapper import EC2Wrapper

fabric_env.skip_bad_hosts = True
fabric_env.user = 'ubuntu'
fabric_env.sudo_user = 'ubuntu'
fabric_env.key_filename = expanduser(path_join(expanduser('~'), '.ssh', 'aws', 'private', 'cscie90.pem'))


class TimeoutError(BaseException):
    pass


def first_run():
    fabric_env.sudo_user = 'root'
    if exists('"$HOME/cscie90-hw8"', use_sudo=True):
        return deploy()

    sudo('apt-get update')
    sudo('apt-get install -q -y --force-yes python-pip python-twisted git')
    sudo('git clone https://github.com/SamuelMarks/cscie90-hw8', user='ubuntu')
    sudo('pip install -r "$HOME/cscie90-hw8/requirements.txt"')


def deploy():
    if not exists('"$HOME/cscie90-hw8"', use_sudo=True):
        return first_run()
    with cd('"$HOME/cscie90-hw8"'):
        sudo('git pull', user='ubuntu')

    with cd('/etc/init'):
        fabric_env.sudo_user = 'root'
        daemon = 'hw8d'
        sudo('> {name}.conf'.format(name=daemon))
        sudo('chmod 700 {name}.conf'.format(name=daemon))
        sudo('''cat << EOF >> {name}.conf
start on runlevel [2345]
stop on runlevel [016]

respawn
setuid nobody
setgid nogroup
exec python "$HOME/cscie90-hw8/hw8/server.py"
EOF
            '''.format(name=daemon))
        sudo('initctl reload-configuration')


def serve():
    if not exists('"$HOME/cscie90-hw8"'):
        raise OSError('Folder: "$HOME/cscie90-hw8" doesn\'t exists but should')

    fabric_env.sudo_user = 'root'
    daemon = 'hw8d'
    sudo('stop {name}'.format(name=daemon), warn_only=True)
    sudo('start {name}'.format(name=daemon))  # Restart is less reliable, especially if it's in a stopped state


def tail():
    daemon = 'hw8d'
    return sudo('tail /var/log/upstart/{name}.log -n 50 -f'.format(name=daemon))


if __name__ == '__main__':
    my_instance_name = 'cscie90_hw8'

    with EC2Wrapper(ami_image_id=my_instance_name, persist=True) as ec2:
        # Launch the base image, set it up and create it:
        hw8_instances = tuple(inst for res in ec2.get_instances() for inst in res.instances
                              if inst.tags.get('Name', '').startswith('hw8'))
        for instance in hw8_instances:
            ec2.set_instance(instance)
            tried = 0
            while instance.state != 'running':
                if tried == 0:
                    print 'instance.state is', instance.state
                    ec2.start_instance()
                    print 'Starting instance and waiting (up to) 2 minutes for it to come up'
                elif tried > 60:
                    raise TimeoutError
                tried += 1
                sleep(2)
            run3 = partial(ec2.run2, host=instance.public_dns_name)
            # print run3(lambda: sudo('whoami'))
            print run3(deploy)
            print run3(serve)
            # print run3(tail)
        if len(hw8_instances) < 2:
            with open('cache', 'w') as f:
                f.write(ec2.create_image_from_instance('hw8_base', 'Base image for creating more instances'))

    base_image_id = open('cache', 'rt').read()
    with EC2Wrapper(ami_image_id=base_image_id, persist=True) as ec2_base0, \
            EC2Wrapper(ami_image_id=base_image_id, persist=True) as ec2_base1, \
            EC2Wrapper(ami_image_id=base_image_id, persist=True) as ec2_base2:
        # Create and launch the three instances:
        instance_id = ec2_base0.create_instance()
        ec2_base0.start_instance(instance_id)
        instance_id = ec2_base1.create_instance()
        ec2_base1.start_instance(instance_id)
        instance_id = ec2_base2.create_instance(placement='ap-southeast-1')
        ec2_base2.start_instance(instance_id)

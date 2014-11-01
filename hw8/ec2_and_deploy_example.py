from os.path import expanduser, join as path_join
from functools import partial

from fabric.context_managers import cd
from fabric.contrib.files import exists
from fabric.api import env as fabric_env, sudo

from EC2Wrapper import EC2Wrapper

fabric_env.skip_bad_hosts = True
fabric_env.user = 'ubuntu'
fabric_env.sudo_user = 'ubuntu'
fabric_env.key_filename = expanduser(path_join(expanduser('~'), '.ssh', 'aws', 'private', 'cscie90.pem'))


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
    if not exists('"$HOME"/cscie90-hw8'):
        raise OSError("Folder: '\"$HOME\"/cscie90-hw8' doesn't exists but should")
    with cd('"$HOME/cscie90-hw8/hw8"'):
        sudo('pkill python && python server.py', user='ubuntu')
        # Obviously in production I would use a proper daemon that would handle PIDs and respawning


if __name__ == '__main__':
    my_instance_name = 'cscie90_hw8'
    with EC2Wrapper(ami_image_id=my_instance_name, persist=False) as ec2:
        hw8_instances = tuple(inst for res in ec2.get_instances() for inst in res.instances
                              if inst.tags.get('Name', '').startswith('hw8'))
        for instance in hw8_instances:
            run3 = partial(ec2.run2, host=getattr(instance, 'public_dns_name'))
            # print run3(lambda: sudo('whoami'))
            print run3(deploy)
            print run3(serve)

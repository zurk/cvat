# SPDX-License-Identifier: MIT
import argparse
import getpass
import json
import logging
import os
from enum import Enum


def get_auth(s):
    """ Parse USER[:PASS] strings and prompt for password if none was
    supplied. """
    user, _, password = s.partition(':')
    password = password or os.environ.get('PASS') or getpass.getpass()
    return user, password


def parse_json_arg(s):
    """ If s is a file load it as JSON if failed try to read by lines, otherwise parse s as JSON."""
    if os.path.exists(s):
        try:
            with open(s, 'r') as fp:
                return json.load(fp)
        except Exception:
            with open(s, 'r') as fp:
                return [line.strip() for line in fp]
    else:
        return json.loads(s)


class ResourceType(Enum):

    LOCAL = 0
    SHARE = 1
    REMOTE = 2

    def __str__(self):
        return self.name.lower()

    def __repr__(self):
        return str(self)

    @staticmethod
    def argparse(s):
        try:
            return ResourceType[s.upper()]
        except KeyError:
            return s


#######################################################################
# Command line interface definition
#######################################################################

parser = argparse.ArgumentParser(
    description='Perform common operations related to CVAT tasks.\n\n'
)
task_subparser = parser.add_subparsers(dest='action')

#######################################################################
# Positional arguments
#######################################################################

parser.add_argument(
    '--auth',
    type=get_auth,
    metavar='USER:[PASS]',
    default=getpass.getuser(),
    help='''defaults to the current user and supports the PASS
            environment variable or password prompt
            (default user: %(default)s).'''
)
parser.add_argument(
    '--server-host',
    type=str,
    default='localhost',
    help='host (default: %(default)s)'
)
parser.add_argument(
    '--server-port',
    type=int,
    default='8080',
    help='port (default: %(default)s)'
)
parser.add_argument(
    '--debug',
    action='store_const',
    dest='loglevel',
    const=logging.DEBUG,
    default=logging.INFO,
    help='show debug output'
)

#######################################################################
# Massive Create
#######################################################################

mass_task_create_parser = task_subparser.add_parser(
    'mass_create',
    description='Create a lot of same CVAT task.'
)
mass_task_create_parser.add_argument(
    '--labels',
    default='[]',
    type=parse_json_arg,
    help='string or file containing JSON labels specification'
)
mass_task_create_parser.add_argument(
    '--bug',
    default='',
    type=str,
    help='bug tracker URL'
)
mass_task_create_parser.add_argument(
    '--image-quality',
    default=50,
    type=int,
    help='Quality of images prerendered on server'
)
mass_task_create_parser.add_argument(
    '--frame-filter',
    default='',
    type=str,
    help='use --frame_filter step=K to use each K-th frame from video'
)
mass_task_create_parser.add_argument(
    '--duplicate-existing',
    action="store_false",
    default=True,
    help='Skips tasks with existsing name. if false create a new one with the same name',
)
mass_task_create_parser.add_argument(
    'resource_type',
    default='local',
    choices=list(ResourceType),
    type=ResourceType.argparse,
    help='type of files specified'
)
mass_task_create_parser.add_argument(
    'resources',
    type=parse_json_arg,
    help='JSON string or file with files you want to submit as tasks.\n'
         'Expected JSON format: list of strings.',
)


#######################################################################
# Create
#######################################################################

task_create_parser = task_subparser.add_parser(
    'create',
    description='Create a new CVAT task.'
)
task_create_parser.add_argument(
    'name',
    type=str,
    help='name of the task'
)
task_create_parser.add_argument(
    '--labels',
    default='[]',
    type=parse_json_arg,
    help='string or file containing JSON labels specification'
)
task_create_parser.add_argument(
    '--bug',
    default='',
    type=str,
    help='bug tracker URL'
)
task_create_parser.add_argument(
    '--image-quality',
    default=50,
    type=int,
    help='Quality of images prerendered on server'
)
task_create_parser.add_argument(
    '--frame-filter',
    default='',
    type=str,
    help='use --frame_filter step=K to use each K-th frame from video'
)
task_create_parser.add_argument(
    'resource_type',
    default='local',
    choices=list(ResourceType),
    type=ResourceType.argparse,
    help='type of files specified'
)
task_create_parser.add_argument(
    'resources',
    type=str,
    help='list of paths or URLs',
    nargs='+'
)

#######################################################################
# Delete
#######################################################################

delete_parser = task_subparser.add_parser(
    'delete',
    description='Delete a CVAT task.'
)
delete_parser.add_argument(
    'task_ids',
    type=int,
    help='list of task IDs',
    nargs='+'
)

#######################################################################
# List
#######################################################################

ls_parser = task_subparser.add_parser(
    'ls',
    description='List all CVAT tasks in simple or JSON format.'
)
ls_parser.add_argument(
    '--json',
    dest='use_json_output',
    default=False,
    action='store_true',
    help='output JSON data'
)

#######################################################################
# Frames
#######################################################################

frames_parser = task_subparser.add_parser(
    'frames',
    description='Download all frame images for a CVAT task.'
)
frames_parser.add_argument(
    'task_id',
    type=int,
    help='task ID'
)
frames_parser.add_argument(
    'frame_ids',
    type=int,
    help='list of frame IDs to download',
    nargs='+'
)
frames_parser.add_argument(
    '--outdir',
    type=str,
    default='',
    help='directory to save images'
)

#######################################################################
# Dump
#######################################################################

dump_parser = task_subparser.add_parser(
    'dump',
    description='Download annotations for a CVAT task.'
)
dump_parser.add_argument(
    'task_id',
    type=int,
    help='task ID'
)
dump_parser.add_argument(
    'filename',
    type=str,
    help='output file'
)
dump_parser.add_argument(
    '--format',
    dest='fileformat',
    type=str,
    default='CVAT XML 1.1 for images',
    help='annotation format (default: %(default)s)'
)

#######################################################################
# Mass Dump
#######################################################################

mass_dump_parser = task_subparser.add_parser(
    'mass_dump',
    description='Download annotations for a CVAT task.'
)
mass_dump_parser.add_argument(
    '--filename-template',
    type=str,
    help='output filename template. Example "./annotations/{name}_{id}.json" where'
         '{name} is task name and {id} is task id. "annotations" diirectory will be created if it does not exist.'
)
mass_dump_parser.add_argument(
    'tasks_id',
    type=int,
    nargs='+',
    help='tasks ID'
)
mass_dump_parser.add_argument(
    '--format',
    dest='fileformat',
    type=str,
    default='CVAT XML 1.1 for images',
    help='annotation format (default: %(default)s)'
)
mass_dump_parser.add_argument(
    '--force',
    default=False,
    action="store_true",
    help='Overwrite file if exists'
)
mass_dump_parser.add_argument(
    '--separator',
    default="_",
    type=str,
    help='Separate name to parts by specified sequence of characters'
)
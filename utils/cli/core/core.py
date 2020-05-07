# SPDX-License-Identifier: MIT
import json
import logging
import os
from pathlib import Path
from time import sleep

import requests
from io import BytesIO
from PIL import Image
from .definition import ResourceType
log = logging.getLogger(__name__)


class CLI():

    def __init__(self, session, api):
        self.api = api
        self.session = session

    def tasks_data(self, task_id, resource_type, resources):
        """ Add local, remote, or shared files to an existing task. """
        url = self.api.tasks_id_data(task_id)
        data = None
        files = None
        if resource_type == ResourceType.LOCAL:
            files = {'client_files[{}]'.format(i): open(f, 'rb') for i, f in enumerate(resources)}
        elif resource_type == ResourceType.REMOTE:
            data = {'remote_files[{}]'.format(i): f for i, f in enumerate(resources)}
        elif resource_type == ResourceType.SHARE:
            data = {'server_files[{}]'.format(i): f for i, f in enumerate(resources)}
        response = self.session.post(url, data=data, files=files)
        response.raise_for_status()

    def tasks_list(self, use_json_output, **kwargs):
        """ List all tasks in either basic or JSON format. """
        tasks = self._get_tasks_list()
        log.info('jobs_id\tproject id\tname')
        tasks = sorted(tasks, key=lambda x: x["id"])
        for t in tasks:
            jobs_id = [job["id"] for segment in t["segments"] for job in segment["jobs"]]
            if use_json_output:
                log.info(json.dumps(t, indent=4))
            else:
                log.info('{jobs_id}\t{id}\t{name}'.format(jobs_id=", ".join(map(str, jobs_id)), **t))

    def _get_tasks_list(self):
        url = self.api.tasks
        response = self.session.get(url)
        response.raise_for_status()
        page = 1
        tasks = []
        while True:
            response_json = response.json()
            for r in response_json['results']:
                tasks.append(r)
            if not response_json['next']:
                return tasks
            page += 1
            url = self.api.tasks_page(page)
            response = self.session.get(url)
            response.raise_for_status()

    def mass_tasks_create(self, labels, bug, resource_type, resources, image_quality, frame_filter, duplicate_existing,
                          **kwargs):
        common_data = {
            'labels': labels,
            'bug': bug,
            'image_quality': image_quality,
            'frame_filter': frame_filter,
            'resource_type': resource_type,
        }
        existing_tasks = {}
        if duplicate_existing:
            tasks = self._get_tasks_list()
            existing_tasks = set(task["name"] for task in tasks)
        for resource in resources:
            resource_path = Path(resource)
            resource_name = resource_path.stem
            if resource_path.suffix not in {".mp4", ".MOV"}:
                log.warning(f"Not mp4 or MOV file in resources ({resource_name}). Skipping")
                continue
            if resource_name in existing_tasks:
                log.info(f"task {resource_name} already exists. Skipping.")
                continue
            data = common_data.copy()
            data["name"] = resource_name
            data["resources"] = [resource]
            self.tasks_create(**data)

    def tasks_create(self, name, labels, bug, resource_type, resources, image_quality, frame_filter,  **kwargs):
        """ Create a new task with the given name and labels JSON and
        add the files to it. """
        url = self.api.tasks
        data = {'name': name,
                'labels': labels,
                'bug_tracker': bug,
                'image_quality': image_quality,
                'frame_filter': frame_filter
                }
        response = self.session.post(url, json=data)
        response.raise_for_status()
        response_json = response.json()
        log.info('Created task ID: {id} NAME: {name}'.format(**response_json))
        self.tasks_data(response_json['id'], resource_type, resources)
        return response_json['id']

    def tasks_delete(self, task_ids, **kwargs):
        """ Delete a list of tasks, ignoring those which don't exist. """
        for task_id in task_ids:
            url = self.api.tasks_id(task_id)
            response = self.session.delete(url)
            try:
                response.raise_for_status()
                log.info('Task ID {} deleted'.format(task_id))
            except requests.exceptions.HTTPError as e:
                if response.status_code == 404:
                    log.info('Task ID {} not found'.format(task_id))
                else:
                    raise e

    def tasks_frame(self, task_id, frame_ids, outdir='', **kwargs):
        """ Download the requested frame numbers for a task and save images as
        task_<ID>_frame_<FRAME>.jpg."""
        for frame_id in frame_ids:
            url = self.api.tasks_id_frame_id(task_id, frame_id)
            response = self.session.get(url)
            response.raise_for_status()
            im = Image.open(BytesIO(response.content))
            outfile = 'task_{}_frame_{:06d}.jpg'.format(task_id, frame_id)
            im.save(os.path.join(outdir, outfile))

    def mass_tasks_dump(self, tasks_id, fileformat, filename_template, force, separator, **kwargs):
        log.info("Fetching tasks data...")
        tasks = self._get_tasks_list()
        task_id_to_name = {task["id"]: task["name"] for task in tasks}
        for task_id in tasks_id:
            if task_id not in task_id_to_name:
                log.warning(f"No task with id {task_id}. Skipping.")
                continue
            name_parts = task_id_to_name[task_id].split(separator)[:2]
            dump_filename = Path(filename_template.format(
                name_part1=name_parts[0], name_part2=name_parts[1], name=task_id_to_name[task_id], id=task_id))
            if dump_filename.exists() and not force:
                log.warning(f"File {dump_filename} exists, skipping dump task with id {task_id}.")
                continue
            parent_dir = Path(dump_filename).parent
            if not parent_dir.exists():
                parent_dir.mkdir(exist_ok=True, parents=True)
            self.tasks_dump(task_id, fileformat, dump_filename)

    def tasks_dump(self, task_id, fileformat, filename, **kwargs):
        """ Download annotations for a task in the specified format
        (e.g. 'YOLO ZIP 1.0')."""
        url = self.api.tasks_id(task_id)
        response = self.session.get(url)
        response.raise_for_status()
        response_json = response.json()

        url = self.api.tasks_id_annotations_filename(task_id,
                                                     response_json['name'],
                                                     fileformat)
        while True:
            response = self.session.get(url)
            response.raise_for_status()
            log.info('STATUS {}'.format(response.status_code))
            if response.status_code == 201:
                break

        response = self.session.get(url + '&action=download')
        response.raise_for_status()

        with open(filename, 'wb') as fp:
            fp.write(response.content)


class CVAT_API_V1():
    """ Build parameterized API URLs """

    def __init__(self, host, port):
        self.base = 'http://{}:{}/api/v1/'.format(host, port)

    @property
    def tasks(self):
        return self.base + 'tasks'

    def tasks_page(self, page_id):
        return self.tasks + '?page={}'.format(page_id)

    def tasks_id(self, task_id):
        return self.tasks + '/{}'.format(task_id)

    def tasks_id_data(self, task_id):
        return self.tasks_id(task_id) + '/data'

    def tasks_id_frame_id(self, task_id, frame_id):
        return self.tasks_id(task_id) + '/frames/{}'.format(frame_id)

    def tasks_id_annotations_filename(self, task_id, name, fileformat):
        return self.tasks_id(task_id) + '/annotations/{}?format={}' \
            .format(name, fileformat)

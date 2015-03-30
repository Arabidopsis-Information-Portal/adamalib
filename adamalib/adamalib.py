#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import subprocess
from contextlib import contextmanager
import tarfile
import tempfile

import requests
import yaml


class APIException(Exception):

    def __init__(self, msg, obj=None):
        super(APIException, self).__init__(msg)
        self.obj = obj


# noinspection PyMethodMayBeStatic
class Adama(object):

    def __init__(self, token, url=None):
        """
        :type token: str
        :type url: str
        :rtype: None
        """
        self.token = token
        self.url = url

    @property
    def utils(self):
        return Utils(self)

    def error(self, message, obj=None):
        """
        :type message: str
        :type obj: object
        :rtype: None
        """
        raise APIException(message, obj)

    def get(self, url, **kwargs):
        """
        :type url: str
        :type kwargs: dict[str, object]
        :rtype: requests.Response
        """
        headers = kwargs.setdefault('headers', {})
        """:type : dict"""
        headers['Authorization'] = 'Bearer {}'.format(self.token)
        return requests.get(self.url + url, **kwargs)

    def get_json(self, url, **kwargs):
        """
        :type url: str
        :type kwargs: dict[str, object]
        :rtype: dict
        """
        response = self.get(url, **kwargs).json()
        if response['status'] != 'success':
            self.error(response['message'], response)
        return response

    def post(self, url, **kwargs):
        """
        :type url: str
        :type kwargs: dict
        :rtype: requests.Response
        """
        return requests.post(self.url + url, **kwargs)

    def delete(self, url):
        """
        :type url: str
        :rtype: None
        """
        requests.delete(self.url + url)

    @property
    def status(self):
        return self.get_json('/status')

    @property
    def namespaces(self):
        nss = self.get_json('/namespaces')['result']
        return Namespaces(self, [Namespace(self, ns['name']) for ns in nss])

    def __getattr__(self, item):
        """
        :type item: str
        :rtype: Namespace
        """
        return Namespace(self, item)


class Namespaces(list):

    def __init__(self, adama, *args, **kwargs):
        super(Namespaces, self).__init__(*args, **kwargs)
        self.adama = adama

    def add(self, **kwargs):
        response = self.adama.post('/namespaces', data=kwargs)
        json_response = response.json()
        if json_response['status'] != 'success':
            self.adama.error(json_response['message'], json_response)
        return Namespace(self.adama, kwargs['name'])


class Namespace(object):

    def __init__(self, adama, namespace):
        """
        :type adama: Adama
        :type namespace: str
        :rtype: None
        """
        self.adama = adama
        self.namespace = namespace
        self._ns_info = None

    def __repr__(self):
        return 'Namespace({})'.format(self.namespace)

    @property
    def services(self):
        srvs = self.adama.get_json(
            '/{}/services'.format(self.namespace))['result']
        return Services(self.adama, self.namespace,
                        [Service(self, srv['name']) for srv in srvs])

    def _preload(self):
        """
        :rtype: dict
        """
        info = self.adama.get_json('/{}'.format(self.namespace))
        self.__dict__.update(info['result'])
        return info

    def __getattr__(self, item):
        """
        :type item: str
        :rtype: Service
        """
        if not item.startswith('_') and self._ns_info is None:
            self._ns_info = self._preload()
            return getattr(self, item)
        return Service(self, item)


class Services(list):

    def __init__(self, adama, namespace, *args, **kwargs):
        """
        :type adama: Adama
        :type namespace: str
        :type args: list
        :type kwargs: dict
        :rtype: None
        """
        super(Services, self).__init__(*args, **kwargs)
        self.adama = adama
        self.namespace = namespace

    def add(self, mod):
        """
        :type mod: module
        :rtype: Service
        """
        code, name, typ = find_code(mod)
        response = self.adama.post(
            '/{}/services'.format(self.namespace),
            files={'code': code}, data={'type': typ})
        try:
            json_response = response.json()
        except ValueError:
            return self.adama.error(response.text, response)
        if json_response['status'] != 'success':
            return self.adama.error(json_response['message'], json_response)
        return Service(Namespace(self.adama, self.namespace), name)


class Service(object):

    def __init__(self, namespace, service):
        """
        :type namespace: Namespace
        :type service: str
        :rtype: None
        """
        self._namespace = namespace
        self.service = service
        self._srv_info = None
        self._version = '0.1'

    def __repr__(self):
        return 'Service({}/{}_{})'.format(
            self._namespace.namespace, self.service, self._version)

    def __getitem__(self, item):
        self._version = item
        return self

    def _preload(self):
        """
        :rtype: dict
        """
        info = self._namespace.adama.get_json('/{}/{}_v{}'.format(
            self._namespace.namespace, self.service, self._version))
        self.__dict__.update(info['result']['service'])
        return info

    def __getattr__(self, item):
        """
        :type item: str
        :rtype:
        """
        if not item.startswith('_') and self._srv_info is None:
            self._srv_info = self._preload()
            return getattr(self, item)
        return Endpoint(self, item)


# noinspection PyProtectedMember
class Endpoint(object):

    def __init__(self, service, endpoint):
        """
        :type service: Service
        :type endpoint: str
        :rtype: None
        """
        self.service = service
        self.endpoint = endpoint
        self.namespace = self.service._namespace
        self.adama = self.service._namespace.adama

    def __call__(self, **kwargs):
        response = self.adama.get('/{}/{}_v{}/{}'.format(
            self.namespace.name, self.service.name,
            self.service.version, self.endpoint),
            params=kwargs)
        if not response.ok:
            self.adama.error(response.text, response)
        if self.service.type in ('query', 'map_filter'):
            json_response = response.json()
            if json_response['status'] != 'success':
                self.adama.error(json_response['message'], json_response)
            return json_response['result']
        else:
            return response


class Utils(object):

    def __init__(self, adama):
        """
        :type adama: Adama
        :rtype: None
        """
        self.adama = adama

    def request(self, url, **kwargs):
        """
        :type url: str
        :type kwargs: dict[str, object]
        :rtype: requests.Response
        """
        resp = requests.get(url, params=kwargs)
        if not resp.ok:
            self.adama.error(resp.text, resp)
        return resp


def find_code(mod):
    """
    :type mod: module
    :rtype: (file, str, str)
    """
    mod_dir = os.path.dirname(os.path.abspath(mod.__file__))
    toplevel_dir = git_top_level(mod_dir)
    code = pack(toplevel_dir)
    metadata = find_metadata(mod_dir, toplevel_dir)
    name = metadata['name']
    typ = metadata['type']
    return code, name, typ


def git_top_level(directory):
    """
    :type directory: str
    :rtype: str
    """
    with chdir(directory):
        try:
            return subprocess.check_output(
                'git rev-parse --show-toplevel'.split()).strip()
        except subprocess.CalledProcessError:
            raise APIException('module not in a git repository')


def pack(directory):
    """
    :type directory: str
    :rtype: file
    """
    temp = tempfile.mkdtemp()
    tar_name = os.path.join(temp, 'code.tgz')
    with chdir(directory), \
            tarfile.open(tar_name, 'w:gz') as tar:
        tar.add('.')
    return open(tar_name)


def find_metadata(directory, toplevel):
    """
    :type directory: str
    :rtype: dict
    """
    if len(os.path.abspath(directory)) < len(os.path.abspath(toplevel)):
        raise APIException('could not find metadata file in '
                           'directory: {}'.format(toplevel))
    try:
        md = open(os.path.join(directory, 'metadata.yml'))
    except IOError:
        return find_metadata(os.path.join(directory, '..'), toplevel)
    return yaml.load(md)


@contextmanager
def chdir(directory):
    old_wd = os.getcwd()
    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(old_wd)

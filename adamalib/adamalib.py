#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import subprocess
from contextlib import contextmanager
import tarfile
import tempfile
import textwrap
import time
import json

import requests
import yaml
from prov.model import ProvDocument


REGISTER_TIMEOUT = 30  # seconds


class APIException(Exception):

    def __init__(self, msg, obj=None):
        super(APIException, self).__init__(msg)
        self.obj = obj


# noinspection PyMethodMayBeStatic
class Adama(object):

    def __init__(self, url, token=None, verify=True):
        """
        :type url: str
        :type token: str
        :type verify: bool
        :rtype: None
        """
        self.url = url
        self.token = token
        self.verify = verify
        self._prov = None

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

    def _auth_request(self, method, url, **kwargs):
        """
        :type method: str
        :type url: str
        :type kwargs: dict[str, object]
        :rtype: requests.Response
        """
        headers = kwargs.setdefault('headers', {})
        """:type : dict"""
        headers['Authorization'] = 'Bearer {}'.format(self.token)
        fun = getattr(requests, method)
        response = fun(self.url + url, verify=self.verify, **kwargs)
        response.raise_for_status()
        return response

    def get(self, url, **kwargs):
        """
        :type url: str
        :type kwargs: dict[str, object]
        :rtype: requests.Response
        """
        return self._auth_request('get', url, **kwargs)

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
        return self._auth_request('post', url, **kwargs)

    def delete(self, url):
        """
        :type url: str
        :rtype: None
        """
        return self._auth_request('delete', url)

    @property
    def status(self):
        return self.get_json('/status')

    @property
    def namespaces(self):
        nss = self.get_json('/namespaces')['result']
        return Namespaces(self, [Namespace(self, ns['name']) for ns in nss])

    def prov(self, obj):
        self._prov = obj

    def __getattr__(self, item):
        """
        :type item: str
        :rtype: Namespace
        """
        return Namespace(self, item)

    def __getitem__(self, item):
        """
        :type item: str
        :rtype: Namespace
        """
        return getattr(self, item)


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
                        [Service(self, srv['name'], srv['version'])
                         for srv in srvs])

    def _preload(self):
        """
        :rtype: dict
        """
        info = self.adama.get_json('/{}'.format(self.namespace))
        self.__dict__.update(info['result'])
        return info

    def delete(self):
        """
        :rtype: None
        """
        self.adama.delete('/{}'.format(self.namespace))
        self._ns_info = None
        self.namespace = '<deleted>'

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

    def add(self, mod, async=False, timeout=REGISTER_TIMEOUT):
        """
        :type mod: module
        :type async: bool
        :rtype: Service|None
        """
        # TODO: if mod is a string, register as a git repo
        code, name, typ, md_path = find_code(mod)
        response = self.adama.post(
            '/{}/services'.format(self.namespace),
            files={'code': code}, data={'type': typ, 'metadata': md_path})
        try:
            json_response = response.json()
        except ValueError:
            return self.adama.error(response.text, response)
        if json_response['status'] != 'success':
            return self.adama.error(json_response['message'], json_response)
        srv = Service(Namespace(self.adama, self.namespace), name)
        if async:
            return srv
        else:
            t = time.time()
            while True:
                if time.time() - t > timeout:
                    return self.adama.error('timeout registering service')
                if getattr(srv, '_error', None):
                    return self.adama.error(srv._message)
                if srv.name is not None:
                    return srv
                time.sleep(0.5)


class Service(object):

    def __init__(self, namespace, service, version='0.1'):
        """
        :type namespace: Namespace
        :type service: str
        :rtype: None
        """
        self._namespace = namespace
        self.service = service
        self._srv_info = None
        self._version = version

    @property
    def _full_name(self):
        return '/{}/{}_v{}'.format(
            self._namespace.namespace, self.service, self._version)

    def __repr__(self):
        return 'Service({})'.format(self._full_name)

    def __getitem__(self, item):
        self._version = item
        return self

    def _preload(self):
        """
        :rtype: dict
        """
        info = self._namespace.adama.get_json(self._full_name)
        result = info['result']
        if result.get('slot') == 'error':
            self._message = result['msg']
            self._error = True
            return None
        if result['service'] is not None:
            self.__dict__.update(info['result']['service'])
            return info

    def __getattr__(self, item):
        """
        :type item: str
        :rtype:
        """
        if item.startswith('_'):
            return getattr(super(Service, self), item)
        if self._srv_info is None:
            self._srv_info = self._preload()
            if self._srv_info is not None:
                return getattr(self, item)
            else:
                return None
        return Endpoint(self, item)

    def delete(self):
        self._namespace.adama.delete(self._full_name)
        self._srv_info = None
        self.service = '<deleted>'


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
            return ProvList(json_response['result'],
                            get_prov_uri(response),
                            self.adama)
        else:
            return response


def get_prov_uri(response):
    try:
        prov_link = "http://www.w3.org/ns/prov#has_provenance"
        return response.links[prov_link]['url']
    except KeyError:
        return None


class ProvList(list):

    def __init__(self, result, prov_url, adama):
        super(ProvList, self).__init__(result)
        self.prov_url = prov_url
        self.adama = adama

    def prov(self, format='json', filename=None):
        if self.prov_url is None:
            raise APIException('no provenance information found')
        response = self.adama.utils.request(self.prov_url, format=format)
        if format in ('json', 'sources'):
            return response.json()
        elif format == 'prov-n':
            return response.text
        elif format == 'prov':
            return ProvDocument.deserialize(
                content=json.dumps(response.json()))
        elif format == 'png':
            return png(response.content, filename)


def png(data, filename):
    # Return an IPython image if possible, or just the content of the png
    # otherwise
    if filename is not None:
        with open(filename, 'w') as out:
            out.write(data)
    else:
        try:
            if __IPYTHON__:
                import IPython.display
                return IPython.display.Image(data=data)
        except NameError:
            pass
        return data


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
        resp = requests.get(url, params=kwargs, verify=self.adama.verify)
        if not resp.ok:
            self.adama.error(resp.text, resp)
        return resp

    def create(self, name, service_type, target=None, git=True):
        """Create a stub for a service.

        If the target is not given, it creates a directory ``name``. It
        optionally can init a git repo.

        :type name: str
        :type service_type: str
        :type target: str
        :type git: bool
        :rtype: str
        """
        if target is None:
            target = name
        os.makedirs(target)
        if not git:
            try:
                git_top_level(target)
            except APIException:
                raise APIException('directory "{}" is not inside a git repo. '
                                   'Either execute this again inside a git '
                                   'repo, or pass the option "git=True" to '
                                   'initialize the directory as a git repo.'
                                   .format(target))
        else:
            init_git(target)
        with chdir(target):
            with open('metadata.yml', 'w') as md:
                md.write(textwrap.dedent(
                    """
                    ---
                    name: {}
                    version: 0.1
                    type: {}
                    main_module: main.py
                    """.format(name, service_type)))
            with open('main.py', 'w') as py:
                py.write(textwrap.dedent(
                    """
                    import json

                    def main(args, adama):
                        print(json.dumps({'key': 'value'}))
                    """))
            with open('__init__.py', 'w'):
                pass


def init_git(directory):
    """
    :type directory: str
    :rtype: None
    """
    with chdir(directory):
        subprocess.check_call('git init'.split())


def find_code(mod):
    """
    :type mod: module
    :rtype: (file, str, str, str)
    """
    mod_dir = os.path.dirname(os.path.abspath(mod.__file__))
    toplevel_dir = git_top_level(mod_dir)
    code = pack(toplevel_dir)
    metadata = find_metadata(mod_dir, toplevel_dir)
    md_dict = yaml.load(open(metadata))
    name = md_dict['name']
    typ = md_dict['type']
    return code, name, typ, os.path.dirname(metadata)[len(toplevel_dir)+1:]


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
    :rtype: str
    """
    if len(os.path.abspath(directory)) < len(os.path.abspath(toplevel)):
        raise APIException('could not find metadata file in '
                           'directory: {}'.format(toplevel))
    try:
        md = os.path.join(directory, 'metadata.yml')
    except IOError:
        return find_metadata(os.path.join(directory, '..'), toplevel)
    return md


@contextmanager
def chdir(directory):
    old_wd = os.getcwd()
    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(old_wd)

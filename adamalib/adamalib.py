#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests


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

    def error(self, message):
        """
        :type message: str
        :rtype: None
        """
        raise APIException(message)

    def get(self, url, **kwargs):
        """
        :type url: str
        :type kwargs: dict[str, object]
        :rtype: requests.Response
        """
        headers = kwargs.setdefault('headers', {})
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
            raise APIException(response['message'], response)
        return response

    def status(self):
        return self.get_json('/status')

    @property
    def namespaces(self):
        nss = self.get_json('/namespaces')['result']
        return [Namespace(self, ns['name']) for ns in nss]

    def __getattr__(self, item):
        """
        :type item: str
        :rtype: Namespace
        """
        return Namespace(self, item)


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

    @property
    def services(self):
        srvs = self.adama.get_json(
            '/{}/services'.format(self.namespace))['result']
        return [Service(self, srv['name']) for srv in srvs]

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


class Service(object):

    def __init__(self, namespace, service):
        """
        :type namespace: Namespace
        :type service: str
        :rtype: None
        """
        self.namespace = namespace
        self.service = service
        self._srv_info = None
        self._version = '0.1'

    def __getitem__(self, item):
        self._version = item
        return self

    def _preload(self):
        """
        :rtype: dict
        """
        info = self.namespace.adama.get_json('/{}/{}_v{}'.format(
            self.namespace.namespace, self.service, self._version))
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


class Endpoint(object):

    def __init__(self, service, endpoint):
        """
        :type service: Service
        :type endpoint: str
        :rtype: None
        """
        self.service = service
        self.endpoint = endpoint

    def __call__(self, **kwargs):
        pass


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
        if resp.ok:
            return resp
        else:
            self.adama.error(resp.text)

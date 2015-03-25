#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests


class APIException(Exception):
    pass


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

    def status(self):
        return self.get('/status').json()

    def namespaces(self):
        return []

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
        self._preload()

    def _preload(self):
        self._ns_info = self.adama.get('/{}'.format(self.namespace)).json()

    def __getattr__(self, item):
        """
        :type item: str
        :rtype: Service
        """
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

    def __getattr__(self, item):
        """
        :type item: str
        :rtype:
        """
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

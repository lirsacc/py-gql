# -*- coding: utf-8 -*-
""" """

import six


class Source(object):

    __slots__ = ('body',)

    def __init__(self, body):
        if isinstance(body, six.binary_type):
            body = body.decode('utf8')
        self.body = body

    def __len__(self):
        return len(self.body)

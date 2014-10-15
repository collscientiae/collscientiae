# coding=utf-8
from __future__ import absolute_import

from .process import ContentProcessor


def test_required_keys_valid():
    for key in ContentProcessor.required_keys:
        assert key in ContentProcessor.allowed_keys

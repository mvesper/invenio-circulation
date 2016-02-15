# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""invenio-circulation 'transaction' handling for indexing and persistence."""

from functools import partial, wraps

from elasticsearch.exceptions import RequestError
from flask import current_app
from invenio_db import db

GLOBAL_PERSISTENT_LOCK = []
GLOBAL_INDEX_STORE = []


def persist(func):
    """Execute the given function in a nested session.
    
    If the given function is callled in the *persistent_context* then it's not
    executed in a nested session.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not GLOBAL_PERSISTENT_LOCK:
            with db.session.begin_nested():
                res = func(*args, **kwargs)
                return res
        else:
            return func(*args, **kwargs)

    return wrapper


def index(func=None, delete=False):
    """Update the index with the result of the given function.
    
    If the given function is callled in the *persistent_context* then the 
    result is not indexed. Instead, it is stored for a potential later
    indexing.
    """
    if func is None:
        return partial(index, delete=delete)

    @wraps(func)
    def wrapper(self_or_cls, *args, **kwargs):
        """Send record for indexing."""
        result = func(self_or_cls, *args, **kwargs)
        if not GLOBAL_PERSISTENT_LOCK:
            try:
                if delete:
                    self_or_cls.indexer.delete(result)
                else:
                    self_or_cls.indexer.index(result)
            except RequestError:
                msg = 'Could not index {0}.'.format(result)
                current_app.logger.exception(msg)
        else:
            GLOBAL_INDEX_STORE.append((self_or_cls.indexer, result, delete))

        return result

    return wrapper


class persistent_context(object):
    """Context manager for indexing/persistence transactions.
    
    Once *persistent_context* is entered the functionality of the functions
    *transactions.persist* and *transactions.index* are altered. Their intended
    effects inure once *persistent_context* is left.
    """

    def __enter__(self):
        """Enter the context manager."""
        if not GLOBAL_PERSISTENT_LOCK:
            db.session.begin_nested()
        GLOBAL_PERSISTENT_LOCK.append(True)

    def __exit__(self, *args, **kwargs):
        """Exit the context manager."""
        global GLOBAL_PERSISTENT_LOCK
        global GLOBAL_INDEX_STORE
        GLOBAL_PERSISTENT_LOCK.pop()

        if isinstance(args[1], Exception):
            if not GLOBAL_PERSISTENT_LOCK:
                GLOBAL_INDEX_STORE = []
                db.session.rollback()
            return

        if not GLOBAL_PERSISTENT_LOCK:
            db.session.commit()
            for indexer, result, delete in GLOBAL_INDEX_STORE:
                if delete:
                    indexer.delete(result)
                else:
                    indexer.index(result)
            del GLOBAL_INDEX_STORE[:]

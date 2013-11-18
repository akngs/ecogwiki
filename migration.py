# -*- coding: utf-8 -*-
import sys
import inspect
from datetime import datetime
from models import MigrationHistory


def migrate():
    histories = MigrationHistory.query().order(-MigrationHistory.performed_at).fetch(1)
    old_version = 0
    if len(histories) != 0:
        old_version = histories[0].version

    performed_migrations = []
    funcs = [(int(name[8:]), name, f) for name, f in inspect.getmembers(sys.modules[__name__]) if name.startswith('version_')]
    funcs.sort(key=lambda x: x[0])
    for i, name, f in funcs:
        if i <= old_version:
            continue
        f()

        history = MigrationHistory()
        history.version = i
        history.performed_at = datetime.now()
        history.put()

        performed_migrations.append(i)

    return performed_migrations


def version_1():
    pass

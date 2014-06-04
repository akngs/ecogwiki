import os
from importlib import import_module

model_exts = []


class ModelExtention(object):
    def on_page_update_content(self, page, modified):
        pass


def scan_exts():
    ext_dir = os.path.join(os.path.dirname(__file__), 'models')
    exts = [f[:-3] for f in os.listdir(ext_dir) if not f.startswith('__') and f.endswith('.py')]
    for extname in exts:
        module = import_module('ext.models.%s' % extname)
        ext = getattr(module, 'Extention')
        model_exts.append(ext())

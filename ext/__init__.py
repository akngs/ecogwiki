import os
from importlib import import_module


model_exts = []
view_exts = []


class ModelExtention(object):
    def on_page_update_content(self, page, modified):
        pass


class ViewExtention(object):
    @classmethod
    def route(cls, path, req, res, head_only):
        for ext in view_exts:
            ext.try_route(path, req, res, head_only)

    def try_route(self, path, req, res, head_only):
        pass


def scan_exts():
    _scan_exts('models', model_exts)
    _scan_exts('views', view_exts)


def _scan_exts(kind, repo):
    ext_dir = os.path.join(os.path.dirname(__file__), kind)
    exts = [f[:-3] for f in os.listdir(ext_dir) if not f.startswith('__') and f.endswith('.py')]
    for extname in exts:
        module = import_module('ext.%s.%s' % (kind, extname))
        ext = getattr(module, 'Extention')
        repo.append(ext())

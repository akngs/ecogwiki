import ext


class Extention(ext.ViewExtention):
    def try_route(self, path, req, res, head_only):
        return False

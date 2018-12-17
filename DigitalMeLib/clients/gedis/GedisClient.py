import imp
import os

from Jumpscale import j
from redis.connection import ConnectionError

TEMPLATE = """
host = "127.0.0.1"
port = 9900
namespace = "default"
adminsecret_ = ""
ssl = false
sslkey = ""
"""

JSConfigBase = j.tools.configmanager.JSBaseClassConfig


class Models():
    def __init__(self):
        pass


class CmdsBase():
    def __init__(self):
        pass


class GedisClient(JSConfigBase):

    def __init__(self, instance, data=None, parent=None, interactive=False, reset=False, configureonly=False):
        JSConfigBase.__init__(self, instance=instance, data=data or {}, parent=parent,
                              template=TEMPLATE, interactive=interactive)

        j.clients.gedis.latest = self
        self.namespace = self.config.data["namespace"]

        self.code_generated_dir = j.sal.fs.joinPaths(j.dirs.VARDIR, "codegen", "gedis", instance, "client")
        j.sal.fs.createDir(self.code_generated_dir)
        j.sal.fs.touch(j.sal.fs.joinPaths(self.code_generated_dir, '__init__.py'))

        if configureonly:
            return

        self.redis = None  # connection to server
        self._models = None
        self._cmds = None
        self.cmds_meta = {}

        self._connect()

        test = self.redis.execute_command("ping")
        if test != b'PONG':
            raise RuntimeError('Can not ping server')
        self._connected = True

        self.redis.execute_command("select", self.namespace)

        schema_urls = self.redis.execute_command("schema_urls")
        self.schema_urls = j.data.serializers.msgpack.loads(schema_urls)

        cmds_meta = self.redis.execute_command("api_meta", self.namespace)
        cmds_meta = j.data.serializers.msgpack.loads(cmds_meta)

        for key, capnpbin in cmds_meta["cmds"].items():
            if "__model_" not in key:
                self.cmds_meta[key] = j.servers.gedis._cmds_get(key, capnpbin).cmds

    def generate(self):
        self._models = Models()

        # this will make sure we have all the local schemas
        def do():
            schemas_meta = self.redis.execute_command("core_schemas_get", self.namespace)
            return schemas_meta

        schemas_meta = self.cache.get("core_schemas_get", method=do, retry=4, die=True)

        schemas_meta = j.data.serializers.msgpack.loads(schemas_meta)
        for key, txt in schemas_meta.items():
            if key not in j.data.schema.schemas:
                schema = j.data.schema.get(txt)

                args = sorted([p for p in schema.properties if p.index], key=lambda p: p.name)
                find_args = ''.join(["{0}={1},".format(p.name, p.default_as_python_code) for p in args]).strip(',')
                kwargs = ''.join(["{0}".format(p.name) for p in args]).strip(',')

                tpath = "%s/templates/ModelBase.py" % (j.clients.gedis._dirpath)
                model_class = j.tools.jinja2.code_python_render(obj_key="model", path=tpath,
                                                                objForHash=schema.text,
                                                                obj=schema, find_args=find_args, kwargs=kwargs)

                model = model_class(client=self)
                self._models.__dict__[schema.url.replace(".", "_")] = model

    @property
    def models(self):
        if self._models is None:
            self.generate()
        return self._models

    @property
    def cmds(self):
        if self._cmds is None:
            self._cmds = CmdsBase()
            for nsfull, cmds_ in self.cmds_meta.items():
                cmds = CmdsBase()
                cmds.cmds = cmds_
                cmds.name = nsfull.replace(".", "_")
                location = nsfull.replace(".", "_")
                cmds_name_lower = nsfull.split(".")[-1].strip().lower()
                cmds.cmds_name_lower = cmds_name_lower

                name = "gedisclient_cmds_%s" % (cmds_name_lower)

                tpath = "%s/templates/template.py" % (j.clients.gedis._dirpath)
                cl = j.tools.jinja2.code_python_render(obj_key="CMDS", path=tpath,
                                                       overwrite=True, name=name,
                                                       objForHash=None, obj=cmds)

                if "__" in cmds_name_lower:
                    cmds_name_lower = cmds_name_lower.split("__", 1)[1]

                self.cmds.__dict__[cmds_name_lower] = cl(client=self, cmds=cmds.cmds)
                self.logger.debug("cmds:%s" % name)
        return self._cmds

    def _connect(self):
        """
        this gets you a redis instance, when executing commands you have to send the name of the function without
        the postfix _cmd as is, do not capitalize it
        if it is testtest_cmd, then you should call it by testtest

        :return: redis instance
        """
        if self.redis is None:
            addr = self.config.data["host"]
            port = self.config.data["port"]
            secret = self.config.data["adminsecret_"]
            ssl_certfile = self.config.data['sslkey']

            if self.config.data['ssl']:
                if not self.config.data['sslkey']:
                    ssl_certfile = j.sal.fs.joinPaths(os.path.dirname(self.code_generated_dir), 'ca.crt')
                self.logger.info("redisclient: %s:%s (ssl:True  cert:%s)" % (addr, port, ssl_certfile))
            else:
                self.logger.info("redisclient: %s:%s " % (addr, port))

            self.redis = j.clients.redis.get(
                ipaddr=addr,
                port=port,
                password=secret,
                ssl=self.config.data['ssl'],
                ssl_ca_certs=ssl_certfile,
                ping=False
            )
        return self.redis

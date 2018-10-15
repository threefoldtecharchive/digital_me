from Jumpscale import j
import msgpack
import struct

JSBASE = j.application.JSBaseClass

#is the base class for the model which gets generated from the template
class BCDBModel(JSBASE):
    def __init__(self, bcdb=None, schema=None, url=None, index_enable=True):
        """
        for query example see http://docs.peewee-orm.com/en/latest/peewee/query_examples.html

        e.g.
        ```
        query = self.index.name.select().where(index.cost > 0)
        for item in self.select(query):
            print(item.name)
        ```
        """

        JSBASE.__init__(self)

        if bcdb is None:
            raise RuntimeError("bcdb should be set")
        self.bcdb = bcdb
        self.namespace = bcdb.namespace
        if url is not None:
            self.schema = j.data.schema.schema_get(url=url)
        else:
            if schema is None:
                schema = SCHEMA  # needs to be in code file
            self.schema = j.data.schema.schema_add(schema)
        self.key = j.core.text.strip_to_ascii_dense(self.schema.url).replace(".","_")
        if bcdb.dbclient.type == "RDB":
            self.db = bcdb.dbclient
        else:
            self.db = self.bcdb.dbclient.namespace_new(name=self.key, maxsize=0, die=False)
            self.db.type = "ZDB"
        self.index_enable = index_enable
        self.json_serialize = self.bcdb.json_serialize

    def index_delete(self):
        self.index.delete().execute()

    def index_load(self):
        self.index_delete()
        j.shell() #TODO:*1
        pass
        # self.logger.info("build index done")

    def destroy(self):
        self.index_delete()
        if self.bcdb.dbclient.type == "RDB":
            for key in self.db.hkeys("bcdb:%s:data" % self.key):
                self.db.hdel("bcdb:%s:data" % self.key,key)
            self.db.delete("bcdb:%s:lastid"%self.key)
        else:
            raise RuntimeError("not implemented yet, need to go to db and remove namespace")

    def delete(self, obj_id):
        """
        """

        if self.db.type == "ZDB":
            self.db.delete(obj_id)
        else:
            self.db.hdel("bcdb:%s:data"%self.key, obj_id)

        #TODO:*1 need to delete the part of index !!!



    def set(self, data, obj_id=None):
        """
        if string -> will consider to be json
        if binary -> will consider data for capnp
        if obj -> will check of JSOBJ
        if ddict will put inside JSOBJ

        @RETURN JSOBJ

        """
        if j.data.types.string.check(data):
            data = j.data.serializers.json.loads(data)
            obj = self.schema.get(data)
        elif j.data.types.bytes.check(data):
            obj = self.schema.get(capnpbin=data)
        elif getattr(data, "_JSOBJ", None):
            obj = data
            if obj_id is None and obj.id is not None:
                obj_id = obj.id
        elif j.data.types.dict.check(data):
            obj = self.schema.get(data)
        else:
            raise RuntimeError("Cannot find data type, str,bin,obj or ddict is only supported")

        # prepare
        obj = self.set_pre(obj)

        if self.json_serialize:
            data = obj._json
        else:

            bdata = obj._data

            # later:
            acl = b""
            crc = b""
            signature = b""

            l = [acl, crc, signature, bdata]
            data = msgpack.packb(l)

        if self.db.type == "ZDB":
            if obj_id is None:
                # means a new one
                obj_id = self.db.set(data)
            else:
                self.db.set(data, key=obj_id)
        else:
            if obj_id is None:
                # means a new one
                obj_id = self.db.incr("bcdb:%s:lastid" % self.key)-1
            self.db.hset("bcdb:%s:data"%self.key, obj_id, data)

        obj.id = obj_id

        self.index_set(obj)

        return obj

    def new(self):
        return self.schema.get()

    def set_pre(self, obj):
        return obj

    def index_set(self, obj):
        pass

    def get(self, id, capnp=False):
        """
        @PARAM id is an int or a key
        @PARAM capnp if true will return data as capnp binary object,
               no hook will be done !
        @RETURN obj    (.index is in obj)
        """

        if id == None:
            raise RuntimeError("id cannot be None")

        if self.db.type == "ZDB":
            data = self.db.get(id)
        else:
            data = self.db.hget("bcdb:%s:data" % self.key, id)

        if not data:
            return None

        return self._get(id,data,capnp=capnp)

    def _get(self, id, data,capnp=False):

        if self.json_serialize:
            res = j.data.serializers.json.loads(data)
            obj = self.schema.get(data=res)
            obj.id = id
            return obj

        else:
            res = msgpack.unpackb(data)

            if len(res) == 4:
                acr, crc, signature, bdata = res
            elif b'schemas' in res:  # this means we are in the metadata record
                return
            else:
                raise RuntimeError("not supported format in table yet")

            if capnp:
                # obj = self.schema.get(capnpbin=bdata)
                # return obj.data
                return bdata
            else:
                obj = self.schema.get(capnpbin=bdata)
                obj.id = id
                return obj

    def iterate(self, method, key_start=None, direction="forward",
                nrrecords=100000, _keyonly=False,
                result=None):
        """walk over the data and apply method as follows

        call for each item:
            '''
            for each:
                result = method(id,obj,result)
            '''
        result is the result of the previous call to the method

        Arguments:
            method {python method} -- will be called for each item found in the file

        Keyword Arguments:
            key_start is the start key, if not given will be start of database when direction = forward, else end

        """

        if self.db.type == "ZDB":
            results = self.db.iterate(key_start=key_start, keyonly=_keyonly)
            results_list = []

            while nrrecords > 0:
                nrrecords -= 1
                try:
                    key, data = next(results)
                    record = self._get(key, data)
                    if record:
                        results_list.append(method(record))
                except StopIteration:
                    break

            return results_list

        else:
            #WE IGNORE Nrrecords
            if not direction=="forward":
                raise RuntimeError("not implemented, only forward iteration supported")
            keys = [int(item.decode()) for item in self.db.hkeys("bcdb:%s:data" % self.key)]
            keys.sort()
            if len(keys)==0:
                return result
            if key_start==None:
                key_start = keys[0]
            for key in keys:
                if key>=key_start:
                    obj = self.get(id=key)
                    result = method(id,obj,result)
            return result

    def get_all(self):
        return self.iterate(lambda obj: obj)

    def __str__(self):
        out = "model:%s\n" % self.key
        out += j.core.text.prefix("    ", self.schema.text)
        return out

    __repr__ = __str__

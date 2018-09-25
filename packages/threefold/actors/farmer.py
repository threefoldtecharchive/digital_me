from Jumpscale import j
JSBASE = j.application.JSBaseClass


class farmer(JSBASE):
    """
    This class functions are actually registered in

    """
    def __init__(self):
        JSBASE.__init__(self)

    def farmers_get(self):
        """

        :return: [farmer_obj]
        """
        pass

    def country_list(self):
        """

        :return: list of countries
        """
        pass

    def node_find(self,country="", farmer_name="",cores_min_nr=0, mem_min_mb=0, ssd_min_gb=0, hd_min_gb=0, nr_max=10 ):
        """

        the capacity checked against is for free (available) capacity (total-used)

        :param country:
        :param farmer_name:
        :param cores_min_nr:
        :param mem_min_mb:
        :param ssd_min_gb:
        :param hd_min_gb:
        :param nr_max: max nr of records to return

        :return: [node_objects]

        """
        pass


    def zos_reserve(self,node_id, vm_name, memory=1024, cores=1, zerotier_net="", adminsecret=""):
        """

        deploys a zero-os for a customer

        :param node_id: is the id of the node on which you want to deploy
        :param vm_name: name freely chosen by customer
        :param memory: Amount of memory in MiB (defaults to 1024)
        :param cores: Number of virtual CPUs (defaults to 1)
        :param zerotier_net: is optional additional network to connect to
        :param adminsecret: is the secret which is set on the redis for the ZOS of the customer

        :return: (node_robot_url, servicesecret, ipaddr_zos,redisport)

        user can now connect the ZOS client to this ipaddress with specified adminsecret over SSL

        each of these ZOS'es is automatically connected to the TF Public Zerotier network (TODO: which one is it)

        ZOS is only connected to the 1 or 2 zerotier networks ! and NAT connection to internet.

        """
        #TODO: *1

    def ubuntu_reserve(self,node_id, vm_name, memory=2048, cores=2, zerotier_net="", pubsshkey=""):
        """

        deploys a ubuntu 18.04 for a customer on a chosen node

        :param node_id: is the id of the node on which you want to deploy
        :param vm_name: name freely chosen by customer
        :param memory: Amount of memory in MiB (defaults to 1024)
        :param cores: Number of virtual CPUs (defaults to 1)
        :param zerotier_net: is optional additional network to connect to
        :param pubsshkey: is the pub key for SSH authorization of the VM

        :return: (node_robot_url, servicesecret,ipaddr_vm)

        user can now connect to this ubuntu over SSH, port 22 (always), only on the 2 zerotiers

        each of these VM's is automatically connected to the TF Public Zerotier network (TODO: which one is it)

        VM is only connected to the 1 or 2 zerotier networks ! and NAT connection to internet.

        """
        #TODO: *1

    def zdb_reserve(self, node_id, name_space, size=100, secret=""):
        """
        :param node_id: is the id of the node on which you want to deploy
        :param size:  in MB
        :param secret: secret to be given to the namespace
        :param name_space: cannot exist yet
        :return: (node_robot_url, servicesecret, ipaddr, port)

        user can now connect to this ZDB using redis client

        each of these VM's is automatically connected to the TF Public Zerotier network (TODO: which one is it)

        VM is only connected to the 1 or 2 zerotier networks ! and NAT connection to internet.
        """

        pass

        # TODO:*1
        # are there other params?

    def webgateways_get(self):
        """

        ```out
        id = 0
        farmer_id = (S)
        farmer_name = (S)
        name =
        location = ""
        ipaddr_public_4 = ""
        ipaddr_public_6 = ""
        ```

        :return:
        """

    def webgateway_http_proxy_set(self,webgateway_id, virtualhost,backend_ipaddr, backend_port, suffix=""):
        """

        will answer on http & https
        will configure the forward in the selected webgateway

        :param webgateway_id: id of the obj you get through self.webgateways_get()
        :param virtualhost: e.g. docsify.js.org
        :param backend_ipaddr: e.g. 10.10.100.10
        :param backend_port: e.g. 8080
        :param suffix: e.f. /mysub/name/
        :return: ???
        """

    def webgateway_http_proxy_set(self,webgateway_id,virtualhost):
        """
        delete all info for the specified virtualhost
        :param webgateway_id:
        :param virtualhost:
        :return:
        """

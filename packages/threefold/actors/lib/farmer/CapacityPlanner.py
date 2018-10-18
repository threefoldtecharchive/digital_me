from Jumpscale import j

JSBASE = j.application.JSBaseClass
VM_TEMPLATE = 'github.com/threefoldtech/0-templates/vm/0.0.1'
ZDB_TEMPLATE = 'github.com/threefoldtech/0-templates/zerodb/0.0.1'
ZEROTIER_TEMPLATE = 'github.com/threefoldtech/0-templates/zerotier_client/0.0.1'
# TODO: Need to set The public ZT_NETWORK with the correct one
PUBLIC_ZT_NETWORK = "35c192ce9bb83c9e"


class CapacityPlanner(JSBASE):
    def __init__(self):
        JSBASE.__init__(self)
        self.models = None

    @staticmethod
    def get_robot(node):
        j.clients.zrobot.get(instance=node['node_zos_id'], data={"url": node['noderobot_ipaddr']})
        return j.clients.zrobot.robots[node['node_zos_id']]

    @staticmethod
    def get_etcd_client(web_gateway):
        etcd_data = {
            "host": web_gateway['etcd_host'],
            "port": web_gateway['etcd_port'],
            "user": "root",
            "password_": web_gateway['etcd_secret']
        }
        return j.clients.etcd.get(web_gateway['name'], data=etcd_data)

    def zos_reserve(self, node, vm_name, zerotier_token, organization, memory=1024, cores=1):
        """
        deploys a zero-os for a customer

        :param node: is the node from model to deploy on
        :param vm_name: name freely chosen by customer
        :param zerotier_token: zerotier token which will be used to get the ip address
        :param memory: Amount of memory in MiB (defaults to 1024)
        :param cores: Number of virtual CPUs (defaults to 1)
        :param organization: is the organization that will be used to get jwt to access zos through redis

        :return: (node_robot_url, service_secret, ipaddr_zos, redis_port)
        user can now connect the ZOS client to this ip address with specified adminsecret over SSL
        each of these ZOS'es is automatically connected to the TF Public Zerotier network
        ZOS is only connected to the 1 or 2 zerotier networks ! and NAT connection to internet.
        """
        flist = 'https://hub.grid.tf/tf-bootable/zero-os-bootable.flist'
        ipxe_url = "https://bootstrap.grid.tf/ipxe/development/{}/organization='{}'%20development"
        ipxe_url = ipxe_url.format(PUBLIC_ZT_NETWORK, organization)
        vm_service, ip_addresses = self._vm_reserve(node=node, vm_name=vm_name, ipxe_url=ipxe_url, cores=cores,
                                                    zerotier_token=zerotier_token, memory=memory, flist=flist)

        return node['noderobot_ipaddr'], vm_service.data['secret'], ip_addresses and ip_addresses[0]['ip_address'], 6379

    def ubuntu_reserve(self, node, vm_name, zerotier_token, memory=2048, cores=2, zerotier_network="", pub_ssh_key=""):
        """
        deploys a ubuntu 18.04 for a customer on a chosen node

        :param node: is the node from model to deploy on
        :param vm_name: name freely chosen by customer
        :param zerotier_token: is zerotier token which will be used to get the ip address
        :param memory: Amount of memory in MiB (defaults to 1024)
        :param cores: Number of virtual CPUs (defaults to 1)
        :param zerotier_network: is optional additional network to connect to
        :param pub_ssh_key: is the pub key for SSH authorization of the VM

        :return: (node_robot_url, service_secret, ipaddr_vm)
        user can now connect to this ubuntu over SSH, port 22 (always), only on the 2 zerotiers
        each of these VM's is automatically connected to the TF Public Zerotier network
        VM is only connected to the 1 or 2 zerotier networks ! and NAT connection to internet.
        """
        configs = []
        if pub_ssh_key:
            configs = [{
                'path': '/root/.ssh/authorized_keys',
                'content': pub_ssh_key,
                'name': 'sshkey'}]
        flist = "https://hub.grid.tf/tf-bootable/ubuntu:lts.flist"
        vm_service, ip_addresses = self._vm_reserve(node=node, vm_name=vm_name, flist=flist,
                                                    zerotier_token=zerotier_token, zerotier_network=zerotier_network,
                                                    memory=memory, cores=cores, configs=configs)
        return node['noderobot_ipaddr'], vm_service.data['secret'], ip_addresses

    def _vm_reserve(self, node, vm_name, zerotier_token, memory=128, cores=1, flist="", ipxe_url="",
                    zerotier_network="", configs=None):
        """
        reserve on zos node (node model obj) a vm

        example flists:
        - https://hub.grid.tf/tf-bootable/ubuntu:latest.flist

        :param node: node model obj (see models/node.toml)
        :param vm_name: the name of vm service to be able to use the service afterwards
        :param flist: flist to boot the vm from
        :param ipxe_url: ipxe url for the ipxe boot script
        :param zerotier_token: is zerotier token which will be used to get the ip address
        :param memory: Amount of memory in MiB (defaults to 128)
        :param cores: Number of virtual CPUs (defaults to 1)
        :param zerotier_network: is optional additional network to connect to
        :param configs: list of config i.e. [{'path': '/root/.ssh/authorized_keys',
                                              'content': 'ssh-rsa AAAAB3NzaC1yc2..',
                                              'name': 'sshkey'}]
        :return:
        """
        # the node robot should send email to the 3bot email address with the right info (access info)
        # for now we store the secret into the reservation table so also this farmer robot can do everything
        # in future this will not be the case !

        # TODO Enable attaching disks
        robot = self.get_robot(node)

        # configure default nic and zerotier nics and clients data
        nics = [{'type': 'default', 'name': 'defaultnic'}]
        zt_data = {'token': zerotier_token}
        zerotier_networks = [PUBLIC_ZT_NETWORK]
        # Add extra network if passed to the method
        if zerotier_network:
            zerotier_networks.append(zerotier_network)
        for i, network_id in enumerate(zerotier_networks):
            extra_zt_nic = {'type': 'zerotier', 'name': 'zt_%s' % i, 'id': network_id, 'ztClient': network_id}
            robot.services.find_or_create(ZEROTIER_TEMPLATE, network_id, data=zt_data)
            nics.append(extra_zt_nic)

        # Create the virtual machine using robot vm template
        data = {
            'name': vm_name,
            'memory': memory,
            'cpu': cores,
            'nics': nics,
            'flist': flist,
            'ipxeUrl': ipxe_url,
            'configs': configs or [],
            'ports': [],
            'tags': [],
            'disks': [],
            'mounts': [],
        }
        vm_service = robot.services.create(VM_TEMPLATE, vm_name, data)
        vm_service.schedule_action('install').wait(die=True)
        print("Getting Zerotier IP ...")
        result = vm_service.schedule_action('info', {"timeout": 120}).wait(die=True).result
        ip_addresses = []
        for nic in result.get('nics', []):
            if nic['type'] == "zerotier":
                ip_addresses.append({"network_id": nic['id'], 'ip_address': nic.get('ip')})

        # Save reservation data
        # reservation = self.models.reservations.new()
        # reservation.secret = vm_service.data['secret']
        # reservation.node_service_id = vm_service.data['guid']
        return vm_service, ip_addresses

    def vm_delete(self, node, vm_name):
        robot = self.get_robot(node)
        vm_service = robot.services.get(name=vm_name)
        vm_service.delete()
        return

    def zdb_reserve(self, node, zdb_name, name_space, disk_type="ssd", disk_size=10, namespace_size=2, secret=""):
        """
        :param node: is the node obj from model
        :param zdb_name: is the name for the zdb
        :param name_space: the first namespace name in 0-db
        :param disk_type: disk type of 0-db (ssd or hdd)
        :param disk_size: disk size of the 0-db in GB
        :param namespace_size: the maximum size in GB for the namespace
        :param secret: secret to be given to the namespace
        :return: (node_robot_url, servicesecret, ip_info)
        """
        data = {
            "diskType": disk_type,
            "size": disk_size,
            "namespaces": [{
                "name": name_space,
                "size": namespace_size,
                "password": secret
            }]
        }
        robot = self.get_robot(node)
        zdb_service = robot.services.create(ZDB_TEMPLATE, zdb_name, data)
        zdb_service.schedule_action('install').wait(die=True)
        print("Getting IP info...")
        ip_info = zdb_service.schedule_action('connection_info').wait(die=True).result
        # reservation = self.models.reservations.new()
        # reservation.secret = zdb_service.data['secret']
        # reservation.node_service_id = zdb_service.data['guid']
        return node['noderobot_ipaddr'], zdb_service.data['secret'], ip_info

    def zdb_delete(self, node, zdb_name):
        robot = self.get_robot(node)
        zdb_service = robot.services.get(name=zdb_name)
        zdb_service.delete()
        return

    def web_gateway_add_host(self, web_gateway, rule_name, domains, backends):
        """
        Register new domain into web gateway
        :param web_gateway: web gateway dict from web gateway model to be used to get services
        :param domains: list of domains to configure
        :param rule_name: the rule convenient name that we can refer to afterwards
        :param backends: list of `ip:port` for the vm service we need to serve (i.e. [192.168.1.2:80])
        """
        # Get etcd client
        etcd_client = self.get_etcd_client(web_gateway)

        # register the domains for coredns use
        # The key for coredns should start with path(/hosts) and the domain reversed
        # i.e. test.com => /hosts/com/test
        for domain in domains:
            domain_parts = domain.strip().split('.')
            for i, ip in enumerate(web_gateway['pubip4']):
                key = "/hosts/{}/x{}".format("/".join(domain_parts[::-1]), i+1)
                value = '{{"host":"{}","ttl":3600}}'.format(ip)
                etcd_client.put(key, value)

        # register the domain for traefik use
        for i, backend in enumerate(backends):
            backend_key = "/traefik/backends/{}/servers/server{}/url".format(rule_name, i+1)
            backend_value = "http://{}".format(backend)
            etcd_client.put(backend_key, backend_value)

        frontend_key1 = "/traefik/frontends/{}/backend".format(rule_name)
        frontend_value1 = rule_name
        etcd_client.put(frontend_key1, frontend_value1)

        frontend_key2 = "/traefik/frontends/{}/routes/base/rule".format(rule_name)
        frontend_value2 = "Host:{}".format(",".join(domains))
        etcd_client.put(frontend_key2, frontend_value2)
        return

    def web_gateway_delete_host(self, web_gateway, rule_name):
        """
        delete a domain from web gateway
        :param web_gateway: web gateway dict from web gateway model to be used to get services
        :param rule_name: the rule we need to delete
        """
        # Get etcd client
        etcd_client = self.get_etcd_client(web_gateway)

        # delete configured domains with this rule_name
        domains_key = "/traefik/frontends/{}/routes/base/rule".format(rule_name)
        domains_value = etcd_client.get(domains_key)
        if not domains_value:
            return
        domains = domains_value[5:]  # domains_value: "Host:test.com,www.test.com"
        for domain in domains.split(","):
            domain_parts = domain.strip().split('.')
            key = "/hosts/{}".format("/".join(domain_parts[::-1]))
            etcd_client.api.delete_prefix(key)

        # remove backend, frontend from traefik etcd config
        backend_key = "/traefik/backends/{}".format(rule_name)
        frontend_key = "/traefik/frontends/{}".format(rule_name)
        etcd_client.api.delete_prefix(backend_key)
        etcd_client.api.delete_prefix(frontend_key)
        return

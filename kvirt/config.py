#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kvirt config class
"""

from jinja2 import Template
from kvirt.defaults import NETS, POOL, CPUMODEL, NUMCPUS, MEMORY, DISKS, DISKSIZE, DISKINTERFACE, DISKTHIN, GUESTID, VNC, CLOUDINIT, RESERVEIP, RESERVEDNS, RESERVEHOST, START, NESTED, TUNNEL, REPORTURL, REPORTDIR, REPORT, REPORTALL, INSECURE, TEMPLATES, TEMPLATESCOMMANDS, KEYS, CMDS, DNS, DOMAIN, SCRIPTS, FILES, ISO, NETMASKS, GATEWAY, SHAREDKEY, TEMPLATE, ENABLEROOT, PLANVIEW, PRIVATEKEY
from kvirt import ansibleutils
from kvirt import dockerutils
from kvirt import nameutils
from kvirt import common
from kvirt.kvm import Kvirt
try:
    from kvirt.vbox import Kbox
except:
    pass
import os
import shutil
import sys
from time import sleep
import webbrowser
import yaml

__version__ = '9.5'


class Kconfig:
    def __init__(self, client=None, debug=False, quiet=False):
        inifile = "%s/.kcli/config.yml" % os.environ.get('HOME')
        if not os.path.exists(inifile):
            if os.path.exists('/Users'):
                _type = 'vbox'
            else:
                _type = 'kvm'
            self.ini = {'default': {'client': 'local'}, 'local': {'pool': 'default', 'type': _type}}
            if not quiet:
                common.pprint("Using local hypervisor as no .kcli/config.yml was found...", color='green')
        else:
            with open(inifile, 'r') as entries:
                try:
                    self.ini = yaml.load(entries)
                except yaml.scanner.ScannerError as err:
                    common.pprint("Couldn't parse yaml in .kcli/config.yml. Leaving...", color='red')
                    common.pprint(err, color='red')
                    sys.exit(1)
                except:
                    self.host = None
                    return
            if 'default' not in self.ini:
                common.pprint("Missing default section in config file. Leaving...", color='red')
                self.host = None
                return
            if 'client' not in self.ini['default']:
                common.pprint("Using local hypervisor as no client was specified...", color='green')
                self.ini['default']['client'] = 'local'
                self.ini['local'] = {}
        self.clients = [e for e in self.ini if e != 'default']
        defaults = {}
        default = self.ini['default']
        defaults['nets'] = default.get('nets', NETS)
        defaults['pool'] = default.get('pool', POOL)
        defaults['template'] = default.get('template', TEMPLATE)
        defaults['cpumodel'] = default.get('cpumodel', CPUMODEL)
        defaults['numcpus'] = int(default.get('numcpus', NUMCPUS))
        defaults['memory'] = int(default.get('memory', MEMORY))
        defaults['disks'] = default.get('disks', DISKS)
        defaults['disksize'] = default.get('disksize', DISKSIZE)
        defaults['diskinterface'] = default.get('diskinterface', DISKINTERFACE)
        defaults['diskthin'] = default.get('diskthin', DISKTHIN)
        defaults['guestid'] = default.get('guestid', GUESTID)
        defaults['vnc'] = bool(default.get('vnc', VNC))
        defaults['cloudinit'] = bool(default.get('cloudinit', CLOUDINIT))
        defaults['reserveip'] = bool(default.get('reserveip', RESERVEIP))
        defaults['reservedns'] = bool(default.get('reservedns', RESERVEDNS))
        defaults['reservehost'] = bool(default.get('reservehost', RESERVEHOST))
        defaults['nested'] = bool(default.get('nested', NESTED))
        defaults['start'] = bool(default.get('start', START))
        defaults['tunnel'] = bool(default.get('tunnel', TUNNEL))
        defaults['insecure'] = bool(default.get('insecure', INSECURE))
        defaults['reporturl'] = default.get('reporturl', REPORTURL)
        defaults['reportdir'] = default.get('reportdir', REPORTDIR)
        defaults['report'] = bool(default.get('report', REPORT))
        defaults['reportall'] = bool(default.get('reportall', REPORTALL))
        defaults['keys'] = default.get('keys', KEYS)
        defaults['cmds'] = default.get('cmds', CMDS)
        defaults['dns'] = default.get('dns', DNS)
        defaults['domain'] = default.get('file', DOMAIN)
        defaults['scripts'] = default.get('script', SCRIPTS)
        defaults['files'] = default.get('files', FILES)
        defaults['iso'] = default.get('iso', ISO)
        defaults['netmasks'] = default.get('netmasks', NETMASKS)
        defaults['gateway'] = default.get('gateway', GATEWAY)
        defaults['sharedkey'] = default.get('sharedkey', SHAREDKEY)
        defaults['enableroot'] = default.get('enableroot', ENABLEROOT)
        defaults['planview'] = default.get('planview', PLANVIEW)
        defaults['privatekey'] = default.get('privatekey', PRIVATEKEY)
        currentplanfile = "%s/.kcli/plan" % os.environ.get('HOME')
        if os.path.exists(currentplanfile):
            self.currentplan = open(currentplanfile).read().strip()
        else:
            self.currentplan = 'kvirt'
        self.default = defaults
        profilefile = default.get('profiles', "%s/.kcli/profiles.yml" % os.environ.get('HOME'))
        profilefile = os.path.expanduser(profilefile)
        if not os.path.exists(profilefile):
            self.profiles = {}
        else:
            with open(profilefile, 'r') as entries:
                self.profiles = yaml.load(entries)
        self.extraclients = {}
        extraclients = []
        if client == 'all':
            clis = [cli for cli in self.clients if self.ini[cli].get('enabled', True)]
            self.client = clis[0]
            extraclients = clis[1:]
        elif client is None:
            self.client = self.ini['default']['client']
        elif ',' in client:
            defaultclient = self.ini['default']['client']
            if defaultclient in client.split(','):
                self.client = defaultclient
                extraclients = [entry for entry in client.split(',') if entry != defaultclient]
            else:
                self.client = client.split(',')[0]
                extraclients = client.split(',')[1:]
        else:
            self.client = client
        if self.client not in self.ini:
            common.pprint("Missing section for client %s in config file. Leaving..." % self.client, color='red')
            os._exit(1)
        options = self.ini[self.client]
        self.host = options.get('host', '127.0.0.1')
        self.port = options.get('port', 22)
        self.user = options.get('user', 'root')
        self.protocol = options.get('protocol', 'ssh')
        self.type = options.get('type', 'kvm')
        self.url = options.get('url', None)
        self.pool = options.get('pool', self.default['pool'])
        self.template = options.get('template', self.default['template'])
        self.tunnel = bool(options.get('tunnel', self.default['tunnel']))
        self.insecure = bool(options.get('insecure', self.default['insecure']))
        self.report = options.get('report', self.default['report'])
        self.reporturl = options.get('reporturl', self.default['reportdir'])
        self.reportdir = options.get('reportdir', self.default['reportdir'])
        self.reportall = options.get('reportall', self.default['reportall'])
        self.enabled = options.get('enabled', True)
        self.nets = options.get('nets', self.default['nets'])
        self.cpumodel = options.get('cpumodel', self.default['cpumodel'])
        self.cpuflags = options.get('cpuflags', [])
        self.numcpus = options.get('numcpus', self.default['numcpus'])
        self.memory = options.get('memory', self.default['memory'])
        self.disks = options.get('disks', self.default['disks'])
        self.disksize = options.get('disksize', self.default['disksize'])
        self.diskinterface = options.get('diskinterface', self.default['diskinterface'])
        self.diskthin = options.get('diskthin', self.default['diskthin'])
        self.guestid = options.get('guestid', self.default['guestid'])
        self.vnc = options.get('vnc', self.default['vnc'])
        self.cloudinit = options.get('cloudinit', self.default['cloudinit'])
        self.reserveip = options.get('reserveip', self.default['reserveip'])
        self.reservedns = options.get('reservedns', self.default['reservedns'])
        self.reservehost = options.get('reservehost', self.default['reservehost'])
        self.nested = options.get('nested', self.default['nested'])
        self.start = options.get('start', self.default['start'])
        self.iso = options.get('iso', self.default['iso'])
        self.keys = options.get('keys', self.default['keys'])
        self.cmds = options.get('cmds', self.default['cmds'])
        self.netmasks = options.get('netmasks', self.default['netmasks'])
        self.gateway = options.get('gateway', self.default['gateway'])
        self.sharedkey = options.get('sharedkey', self.default['sharedkey'])
        self.enableroot = options.get('enableroot', self.default['enableroot'])
        self.planview = options.get('planview', self.default['planview'])
        self.dns = options.get('dns', self.default['dns'])
        self.domain = options.get('domain', self.default['domain'])
        self.scripts = options.get('scripts', self.default['scripts'])
        self.files = options.get('files', self.default['files'])
        self.privatekey = options.get('privatekey', self.default['privatekey'])
        if not self.enabled:
            k = None
        else:
            if self.type == 'vbox':
                k = Kbox()
            else:
                if self.host is None:
                    common.pprint("Problem parsing your configuration file", color='red')
                    os._exit(1)
                k = Kvirt(host=self.host, port=self.port, user=self.user, protocol=self.protocol, url=self.url, debug=debug)
            if k.conn is None:
                common.pprint("Couldn't connect to specify hypervisor %s. Leaving..." % self.host, color='red')
                os._exit(1)
            for extraclient in extraclients:
                if extraclient not in self.ini:
                    common.pprint("Missing section for client %s in config file. Leaving..." % extraclient, color='red')
                    os._exit(1)
                options = self.ini[extraclient]
                if 'host' not in options and 'url' not in options:
                    common.pprint("Missing connection information for client %s in config file. Leaving..." % extraclient, color='red')
                    os._exit(1)
                host = options.get('host')
                port = options.get('port', 22)
                user = options.get('user', 'root')
                protocol = options.get('protocol', 'ssh')
                url = options.get('url', None)
                e = Kvirt(host=host, port=port, user=user, protocol=protocol, url=url, debug=debug)
                self.extraclients[extraclient] = e
                if e.conn is None:
                    common.pprint("Couldn't connect to specify hypervisor %s. Leaving..." % extraclient, color='red')
                    os._exit(1)
            if extraclients:
                self.extraclients[self.client] = k
        self.k = k

    def create_vm(self, name, profile, ip1=None, ip2=None, ip3=None, ip4=None, overrides={}):
        if name is None:
            name = nameutils.get_random_name()
        k = self.k
        tunnel = self.tunnel
        if profile is None:
            common.pprint("Missing profile", color='red')
            os._exit(1)
        vmprofiles = {k: v for k, v in self.profiles.iteritems() if 'type' not in v or v['type'] == 'vm'}
        common.pprint("Deploying vm %s from profile %s..." % (name, profile), color='green')
        if profile not in vmprofiles:
            common.pprint("profile %s not found. Trying to use the profile as template and default values..." % profile, color='blue')
            vmprofiles[profile] = {'template': profile}
        profilename = profile
        profile = vmprofiles[profile]
        template = profile.get('template', self.template)
        plan = 'kvirt'
        nets = profile.get('nets', self.nets)
        cpumodel = profile.get('cpumodel', self.cpumodel)
        cpuflags = profile.get('cpuflags', self.cpuflags)
        numcpus = profile.get('numcpus', self.numcpus)
        memory = profile.get('memory', self.memory)
        pool = profile.get('pool', self.pool)
        disks = profile.get('disks', self.disks)
        disksize = profile.get('disksize', self.disksize)
        diskinterface = profile.get('diskinterface', self.diskinterface)
        diskthin = profile.get('diskthin', self.diskthin)
        guestid = profile.get('guestid', self.guestid)
        iso = profile.get('iso', self.iso)
        vnc = profile.get('vnc', self.vnc)
        cloudinit = profile.get('cloudinit', self.cloudinit)
        reserveip = profile.get('reserveip', self.reserveip)
        reservedns = profile.get('reservedns', self.reservedns)
        reservehost = profile.get('reservehost', self.reservehost)
        nested = profile.get('nested', self.nested)
        start = profile.get('start', self.start)
        report = profile.get('report', self.report)
        reportall = profile.get('reportall', self.reportall)
        keys = profile.get('keys', self.keys)
        cmds = common.remove_duplicates(self.cmds + profile.get('cmds', []))
        netmasks = profile.get('netmasks', self.netmasks)
        gateway = profile.get('gateway', self.gateway)
        dns = profile.get('dns', self.dns)
        domain = profile.get('domain', self.domain)
        scripts = common.remove_duplicates(self.scripts + profile.get('scripts', []))
        files = profile.get('files', self.files)
        enableroot = profile.get('enableroot', self.enableroot)
        privatekey = profile.get('privatekey', self.privatekey)
        scriptcmds = []
        if scripts:
            for script in scripts:
                script = os.path.expanduser(script)
                if not os.path.exists(script):
                    common.pprint("Script %s not found.Ignoring..." % script, color='red')
                    os._exit(1)
                else:
                    scriptlines = [Template(line.strip()).render() for line in open(script).readlines() if line != '\n']
                    if scriptlines:
                        scriptcmds.extend(scriptlines)
        cmds = cmds + scriptcmds
        if reportall:
            reportcmd = 'curl -s -X POST -d "name=%s&status=Running&report=`cat /var/log/cloud-init.log`" %s/report >/dev/null' % (name, self.reporturl)
            finishcmd = 'curl -s -X POST -d "name=%s&status=OK&report=`cat /var/log/cloud-init.log`" %s/report >/dev/null' % (name, self.reporturl)
            if not cmds:
                cmds = [finishcmd]
            else:
                results = []
                for cmd in cmds[:-1]:
                    results.append(cmd)
                    results.append(reportcmd)
                results.append(cmds[-1])
                results.append(finishcmd)
                cmds = results
        elif report:
            reportcmd = ['curl -s -X POST -d "name=%s&status=OK&report=`cat /var/log/cloud-init.log`" %s/report /dev/null' % (name, self.reporturl)]
            cmds = cmds + reportcmd
        ips = [ip1, ip2, ip3, ip4]
        if privatekey:
            privatekeyfile = None
            if os.path.exists("%s/.ssh/id_rsa" % os.environ['HOME']):
                privatekeyfile = "%s/.ssh/id_rsa" % os.environ['HOME']
            elif os.path.exists("%s/.ssh/id_rsa" % os.environ['HOME']):
                privatekeyfile = "%s/.ssh/id_dsa" % os.environ['HOME']
            if privatekeyfile is not None:
                privatekey = open(privatekeyfile).read().strip()
                if files:
                    files.append({'path': '/root/.ssh/id_rsa', 'content': privatekey})
                else:
                    files = [{'path': '/root/.ssh/id_rsa', 'content': privatekey}]
        result = k.create(name=name, plan=plan, profile=profilename, cpumodel=cpumodel, cpuflags=cpuflags, numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool, template=template, disks=disks, disksize=disksize, diskthin=diskthin, diskinterface=diskinterface, nets=nets, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit), reserveip=bool(reserveip), reservedns=bool(reservedns), reservehost=bool(reservehost), start=bool(start), keys=keys, cmds=cmds, ips=ips, netmasks=netmasks, gateway=gateway, dns=dns, domain=domain, nested=bool(nested), tunnel=tunnel, files=files, enableroot=enableroot, overrides=overrides)
        if result['result'] != 'success':
            return result
        ansible = profile.get('ansible')
        if ansible is not None:
            for element in ansible:
                if 'playbook' not in element:
                    continue
                playbook = element['playbook']
                if 'variables' in element:
                    variables = element['variables']
                if 'verbose' in element:
                    verbose = element['verbose']
                else:
                    verbose = False
                # k.play(name, playbook=playbook, variables=variables, verbose=verbose)
                with open("/tmp/%s.inv" % name, "w") as f:
                    inventory = ansibleutils.inventory(k, name)
                    if inventory is not None:
                        if variables is not None:
                            for variable in variables:
                                if not isinstance(variable, dict) or len(variable.keys()) != 1:
                                    continue
                                else:
                                    key, value = variable.keys()[0], variable[variable.keys()[0]]
                                    inventory = "%s %s=%s" % (inventory, key, value)
                    if self.tunnel:
                        inventory = "%s ansible_ssh_common_args='-o ProxyCommand=\"ssh -p %s -W %%h:%%p %s@%s\"'\n" % (inventory, self.port, self.user, self.host)
                    f.write("%s\n" % inventory)
                ansiblecommand = "ansible-playbook"
                if verbose:
                    ansiblecommand = "%s -vvv" % ansiblecommand
                ansibleconfig = os.path.expanduser('~/.ansible.cfg')
                with open(ansibleconfig, "w") as f:
                    f.write("[ssh_connection]\nretries=10\n")
                print("Running: %s -i /tmp/%s.inv %s" % (ansiblecommand, name, playbook))
                os.system("%s -i /tmp/%s.inv %s" % (ansiblecommand, name, playbook))
        common.lastvm(name)
        return {'result': 'success'}

    def list_plans(self):
        k = self.k
        vms = {}
        plans = []
        for vm in sorted(k.list(), key=lambda x: x[4]):
                vmname = vm[0]
                plan = vm[4]
                if plan in vms:
                    vms[plan].append(vmname)
                else:
                    vms[plan] = [vmname]
        for plan in sorted(vms):
            planvms = ','.join(vms[plan])
            plans.append([plan, planvms])
        return plans

    def list_profiles(self):
        default_disksize = '10'
        default = self.default
        results = []
        for profile in sorted(self.profiles):
                info = self.profiles[profile]
                profiletype = info.get('type', '')
                if profiletype == 'container':
                    continue
                numcpus = info.get('numcpus', default['pool'])
                memory = info.get('memory', default['memory'])
                pool = info.get('pool', default['pool'])
                diskinfo = []
                disks = info.get('disks', default['disks'])
                for disk in disks:
                    if disk is None:
                        size = default_disksize
                    elif isinstance(disk, int):
                        size = str(disk)
                    elif isinstance(disk, dict):
                        size = str(disk.get('size', default_disksize))
                    diskinfo.append(size)
                diskinfo = ','.join(diskinfo)
                netinfo = []
                nets = info.get('nets', default['nets'])
                for net in nets:
                    if isinstance(net, str):
                        netname = net
                    elif isinstance(net, dict) and 'name' in net:
                        netname = net['name']
                    netinfo.append(netname)
                netinfo = ','.join(netinfo)
                template = info.get('template', '')
                cloudinit = info.get('cloudinit', default['cloudinit'])
                nested = info.get('nested', default['nested'])
                reservedns = info.get('reservedns', default['reservedns'])
                reservehost = info.get('reservehost', default['reservehost'])
                results.append([profile, numcpus, memory, pool, diskinfo, template, netinfo, cloudinit, nested, reservedns, reservehost])
        return results

    def list_containerprofiles(self):
        results = []
        for profile in sorted(self.profiles):
                info = self.profiles[profile]
                if 'type' not in info or info['type'] != 'container':
                    continue
                else:
                    image = next((e for e in [info.get('image'), info.get('template')] if e is not None), '')
                    nets = info.get('nets', '')
                    ports = info.get('ports', '')
                    volumes = next((e for e in [info.get('volumes'), info.get('disks')] if e is not None), '')
                    # environment = profile.get('environment', '')
                    cmd = info.get('cmd', '')
                    results.append([profile, image, nets, ports, volumes, cmd])
        return results

    def list_repos(self):
        reposfile = "%s/.kcli/repos.yml" % os.environ.get('HOME')
        if not os.path.exists(reposfile) or os.path.getsize(reposfile) == 0:
            repos = {}
        else:
            with open(reposfile, 'r') as entries:
                try:
                    repos = yaml.load(entries)
                except yaml.scanner.ScannerError:
                    common.pprint("Couldn't properly parse .kcli/repos.yml. Leaving...", color='red')
                    sys.exit(1)
        return repos

    def list_products(self, group=None):
        configdir = "%s/.kcli" % os.environ.get('HOME')
        if not os.path.exists(configdir):
            return []
        else:
            products = []
            repodirs = [d.replace('repo_', '') for d in os.listdir(configdir) if os.path.isdir("%s/%s" % (configdir, d)) and d.startswith('repo_')]
            for repo in repodirs:
                repometa = "%s/repo_%s/KMETA" % (configdir, repo)
                if not os.path.exists(repometa):
                    continue
                else:
                    with open(repometa, 'r') as entries:
                        try:
                            repoproducts = yaml.load(entries)
                            for repoproduct in repoproducts:
                                repoproduct['repo'] = repo
                                if 'group' not in repoproduct:
                                    repoproduct['group'] = 'notavailable'
                                if 'file' not in repoproduct:
                                    repoproduct['file'] = 'kcli_plan.yml'
                                products.append(repoproduct)
                        except yaml.scanner.ScannerError:
                            common.pprint("Couldn't properly parse .kcli/repo. Leaving...", color='red')
                            continue
            if group is not None:
                products = [product for product in products if 'group' in product and product['group'] == group]
            return products

    def create_repo(self, name, url):
        self.update_repo(name, url=url)
        reposfile = "%s/.kcli/repos.yml" % os.environ.get('HOME')
        if not os.path.exists(reposfile) or os.path.getsize(reposfile) == 0:
            entry = "%s: %s" % (name, url)
            open(reposfile, 'w').write(entry)
        else:
            with open(reposfile, 'r') as entries:
                try:
                    repos = yaml.load(entries)
                except yaml.scanner.ScannerError:
                    common.pprint("Couldn't properly parse .kcli/repos.yml. Leaving...", color='red')
                    sys.exit(1)
            if name in repos:
                if repos[name] == url:
                    common.pprint("Entry for name allready there. Leaving...", color='blue')
                    return {'result': 'success'}
                else:
                    common.pprint("Updating url for repo %s" % name, color='green')
            repos[name] = url
            with open(reposfile, 'w') as reposfile:
                for repo in sorted(repos):
                    url = repos[repo]
                    entry = "%s: %s\n" % (repo, url)
                    reposfile.write(entry)
        return {'result': 'success'}

    def update_repo(self, name, url=None):
        reposfile = "%s/.kcli/repos.yml" % os.environ.get('HOME')
        repodir = "%s/.kcli/repo_%s" % (os.environ.get('HOME'), name)
        if url is None:
            if not os.path.exists(reposfile) or os.path.getsize(reposfile) == 0:
                common.pprint("Empty .kcli/repos.yml. Leaving...", color='red')
                sys.exit(1)
            else:
                with open(reposfile, 'r') as entries:
                    try:
                        repos = yaml.load(entries)
                    except yaml.scanner.ScannerError:
                        common.pprint("Couldn't properly parse .kcli/repos.yml. Leaving...", color='red')
                        sys.exit(1)
                if name not in repos:
                    common.pprint("Entry for name allready there. Leaving...", color='red')
                    sys.exit(1)
            url = "%s/KMETA" % repos[name]
        elif 'KMETA' not in url:
            url = "%s/KMETA" % url
        common.fetch(url, repodir)
        return {'result': 'success'}

    def delete_repo(self, name):
        reposfile = "%s/.kcli/repos.yml" % os.environ.get('HOME')
        repodir = "%s/.kcli/repo_%s" % (os.environ.get('HOME'), name)
        if not os.path.exists(reposfile):
            common.pprint("Repo %s not found. Leaving..." % name, color='blue')
            return {'result': 'success'}
        else:
            with open(reposfile, 'r') as entries:
                try:
                    repos = yaml.load(entries)
                except yaml.scanner.ScannerError:
                    common.pprint("Couldn't properly parse .kcli/repos.yml. Leaving...", color='red')
                    sys.exit(1)
            if name in repos:
                del repos[name]
            else:
                common.pprint("Repo %s not found. Leaving..." % name, color='blue')
            if not repos:
                os.remove(reposfile)
            with open(reposfile, 'w') as reposfile:
                for repo in sorted(repos):
                    url = repos[repo]
                    entry = "%s: %s\n" % (repo, url)
                    reposfile.write(entry)
            if os.path.isdir(repodir):
                shutil.rmtree(repodir)
            return {'result': 'success'}

    def info_product(self, name, repo=None):
        """Info product"""
        if repo is not None:
            products = [product for product in self.list_products() if product['name'] == name and product['repo'] == repo]
        else:
            products = [product for product in self.list_products() if product['name'] == name]
        if len(products) == 0:
                    common.pprint("Product not found. Leaving...", color='red')
                    sys.exit(1)
        elif len(products) > 1:
                    common.pprint("Product found in several repos. Specify one...", color='red')
                    sys.exit(1)
        else:
            product = products[0]
            repo = product['repo']
            group = product['group']
            template = product.get('template')
            parameters = product.get('parameters')
            if group is not None:
                print("group: %s" % group)
            if template is not None:
                print("template: %s" % template)
            if parameters is not None:
                print("Available parameters:")
                for parameter in parameters:
                    print("%s: %s" % (parameter, parameters[parameter]))

    def create_product(self, name, repo=None, plan=None, keep=False, overrides={}):
        """Create product"""
        if repo is not None:
            products = [product for product in self.list_products() if product['name'] == name and product['repo'] == repo]
        else:
            products = [product for product in self.list_products() if product['name'] == name]
        if len(products) == 0:
                    common.pprint("Product not found. Leaving...", color='red')
                    sys.exit(1)
        elif len(products) > 1:
                    common.pprint("Product found in several repos. Specify one...", color='red')
                    sys.exit(1)
        else:
            product = products[0]
            plan = nameutils.get_random_name() if plan is None else plan
            url = product['url']
            inputfile = product['file']
            repo = product['repo']
            group = product['group']
            template = product.get('template')
            parameters = product.get('parameters')
            should_clean = False
            if template is not None:
                print("Note that this product uses template: %s" % template)
            if parameters is not None:
                for parameter in parameters:
                    if parameter in overrides:
                        print("Using %s: %s" % (parameter, overrides[parameter]))
            if not os.path.exists(group):
                should_clean = True
                self.plan(plan, get=url, path=group, inputfile=inputfile)
            else:
                common.pprint("Using existing directory %s" % group, color='green')
            os.chdir(group)
            common.pprint("Running: kcli plan -f %s %s" % (inputfile, plan), color='green')
            self.plan(plan, inputfile=inputfile, overrides=overrides)
            os.chdir('..')
            common.pprint("Product can be deleted with: kcli plan -d %s" % (plan), color='green')
            if not keep and should_clean:
                shutil.rmtree(group)
        return {'result': 'success', 'plan': plan}

    def plan(self, plan, ansible=False, get=None, path=None, autostart=False, container=False, noautostart=False, inputfile=None, start=False, stop=False, delete=False, delay=0, force=True, topologyfile=None, scale=None, overrides={}):
        """Create/Delete/Stop/Start vms from plan file"""
        k = self.k
        newvms = []
        vmprofiles = {key: value for key, value in self.profiles.iteritems() if 'type' not in value or value['type'] == 'vm'}
        containerprofiles = {key: value for key, value in self.profiles.iteritems() if 'type' in value and value['type'] == 'container'}
        tunnel = self.tunnel
        if plan is None:
            plan = nameutils.get_random_name()
        if path is None:
            path = plan
        if delete:
            networks = []
            if plan == '':
                common.pprint("That would delete every vm...Not doing that", color='red')
                os._exit(1)
            if not force:
                common.confirm('Are you sure about deleting plan %s' % plan)
            found = False
            for vm in sorted(k.list()):
                name = vm[0]
                description = vm[4]
                if description == plan:
                    vmnetworks = k.vm_ports(name)
                    for network in vmnetworks:
                        if network != 'default' and network not in networks:
                            networks.append(network)
                    k.delete(name)
                    common.pprint("VM %s deleted!" % name, color='green')
                    found = True
            if container:
                for cont in sorted(dockerutils.list_containers(k)):
                    name = cont[0]
                    container_plan = cont[3]
                    if container_plan == plan:
                        dockerutils.delete_container(k, name)
                        common.pprint("Container %s deleted!" % name, color='green')
                        found = True
            # for network in k.list_networks():
            #    if 'plan' in network and network['plan'] == plan:
            for network in networks:
                k.delete_network(network)
                common.pprint("Unused network %s deleted!" % network, color='green')
                found = True
            if found:
                common.pprint("Plan %s deleted!" % plan, color='green')
            else:
                common.pprint("Nothing to do for plan %s" % plan, color='red')
                os._exit(1)
            return {'result': 'success'}
        if autostart:
            common.pprint("Set vms from plan %s to autostart" % (plan), color='green')
            for vm in sorted(k.list()):
                name = vm[0]
                description = vm[4]
                if description == plan:
                    k.update_start(name, start=True)
                    common.pprint("%s set to autostart!" % name, color='green')
            return {'result': 'success'}
        if noautostart:
            common.pprint("Preventing vms from plan %s to autostart" % (plan), color='green')
            for vm in sorted(k.list()):
                name = vm[0]
                description = vm[4]
                if description == plan:
                    k.update_start(name, start=False)
                    common.pprint("%s prevented to autostart!" % name, color='green')
            return {'result': 'success'}
        if start:
            common.pprint("Starting vms from plan %s" % (plan), color='green')
            for vm in sorted(k.list()):
                name = vm[0]
                description = vm[4]
                if description == plan:
                    k.start(name)
                    common.pprint("VM %s started!" % name, color='green')
            if container:
                for cont in sorted(dockerutils.list_containers(k)):
                    name = cont[0]
                    containerplan = cont[3]
                    if containerplan == plan:
                        dockerutils.start_container(k, name)
                        common.pprint("Container %s started!" % name, color='green')
            common.pprint("Plan %s started!" % plan, color='green')
            return {'result': 'success'}
        if stop:
            common.pprint("Stopping vms from plan %s" % (plan), color='green')
            for vm in sorted(k.list()):
                name = vm[0]
                description = vm[4]
                if description == plan:
                    k.stop(name)
                    common.pprint("%s stopped!" % name, color='green')
            if container:
                for cont in sorted(dockerutils.list_containers(k)):
                    name = cont[0]
                    containerplan = cont[3]
                    if containerplan == plan:
                        dockerutils.stop_container(k, name)
                        common.pprint("Container %s stopped!" % name, color='green')
            common.pprint("Plan %s stopped!" % plan, color='green')
            return {'result': 'success'}
        if get is not None:
            common.pprint("Retrieving specified plan from %s to %s" % (get, path), color='green')
            if not os.path.exists(path):
                common.fetch(get, path)
            return {'result': 'success'}
        if inputfile is None:
            inputfile = 'kcli_plan.yml'
            common.pprint("using default input file kcli_plan.yml", color='green')
        inputfile = os.path.expanduser(inputfile)
        basedir = os.path.dirname(inputfile)
        if not os.path.exists(inputfile):
            common.pprint("No input file found nor default kcli_plan.yml.Leaving....", color='red')
            os._exit(1)
        with open(inputfile, 'r') as entries:
            entries = yaml.load(entries)
            vmentries = [entry for entry in entries if 'type' not in entries[entry] or entries[entry]['type'] == 'vm']
            diskentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'disk']
            networkentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'network']
            containerentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'container']
            ansibleentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'ansible']
            profileentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'profile']
            templateentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'template']
            poolentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'pool']
            planentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'plan']
            dnsentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'dns']
            for p in profileentries:
                vmprofiles[p] = entries[p]
            if planentries:
                common.pprint("Deploying Plans...", color='green')
                for planentry in planentries:
                    details = entries[planentry]
                    url = details.get('url')
                    path = details.get('path', planentry)
                    inputfile = details.get('file', 'kcli_plan.yml')
                    run = details.get('run', False)
                    if url is None:
                        common.pprint("Missing Url for plan %s. Not creating it..." % planentry, color='blue')
                        continue
                    else:
                        common.pprint("Grabbing Plan %s!" % planentry, color='green')
                        if not os.path.exists(planentry):
                            os.mkdir(planentry)
                            common.fetch(url, path)
                        if run:
                            os.chdir(path)
                            common.pprint("Running kcli plan -f %s %s" % (inputfile, plan), color='green')
                            self.plan(plan, ansible=False, get=None, path=path, autostart=False, container=False, noautostart=False, inputfile=inputfile, start=False, stop=False, delete=False, delay=delay)
                            os.chdir('..')
                return {'result': 'success'}
            if networkentries:
                common.pprint("Deploying Networks...", color='green')
                for net in networkentries:
                    netprofile = entries[net]
                    if k.net_exists(net):
                        common.pprint("Network %s skipped!" % net, color='blue')
                        continue
                    cidr = netprofile.get('cidr')
                    nat = bool(netprofile.get('nat', True))
                    if cidr is None:
                        common.pprint("Missing Cidr for network %s. Not creating it..." % net, color='blue')
                        continue
                    dhcp = netprofile.get('dhcp', True)
                    domain = netprofile.get('domain')
                    pxe = netprofile.get('pxe')
                    result = k.create_network(name=net, cidr=cidr, dhcp=dhcp, nat=nat, domain=domain, plan=plan, pxe=pxe)
                    common.handle_response(result, net, element='Network ')
            if poolentries:
                common.pprint("Deploying Pool...", color='green')
                pools = k.list_pools()
                for pool in poolentries:
                    if pool in pools:
                        common.pprint("Pool %s skipped!" % pool, color='blue')
                        continue
                    else:
                        poolprofile = entries[pool]
                        poolpath = poolprofile.get('path')
                        if poolpath is None:
                            common.pprint("Pool %s skipped as path is missing!" % pool, color='blue')
                            continue
                        k.create_pool(pool, poolpath)
            if templateentries:
                common.pprint("Deploying Templates...", color='green')
                templates = [os.path.basename(t) for t in k.volumes()]
                for template in templateentries:
                    if template in templates:
                        common.pprint("Template %s skipped!" % template, color='blue')
                        continue
                    else:
                        templateprofile = entries[template]
                        pool = templateprofile.get('pool', self.pool)
                        url = templateprofile.get('url')
                        cmd = templateprofile.get('cmd')
                        if url is None:
                            common.pprint("Template %s skipped as url is missing!" % template, color='blue')
                            continue
                        if not url.endswith('qcow2') and not url.endswith('img') and not url.endswith('qc2'):
                            common.pprint("Opening url %s for you to grab complete url for %s" % (url, template), color='blue')
                            webbrowser.open(url, new=2, autoraise=True)
                            url = raw_input("Copy Url:\n")
                            if url.strip() == '':
                                common.pprint("Template %s skipped as url is empty!" % template, color='blue')
                                continue
                        result = k.add_image(url, pool, cmd=cmd)
                        common.handle_response(result, template, element='Template ', action='Added')
            if dnsentries:
                common.pprint("Deploying Dns Entry...", color='green')
                for dnsentry in dnsentries:
                    dnsprofile = entries[dnsentry]
                    dnsdomain = dnsprofile.get('domain')
                    dnsnet = dnsprofile.get('net')
                    dnsdomain = dnsprofile.get('domain', dnsnet)
                    dnsip = dnsprofile.get('ip')
                    dnsalias = dnsprofile.get('alias', [])
                    if dnsip is None:
                        common.pprint("Missing ip. Skipping!", color='blue')
                        return
                    if dnsnet is None:
                        common.pprint("Missing net. Skipping!", color='blue')
                        return
                    k.reserve_dns(name=dnsentry, nets=[dnsnet], domain=dnsdomain, ip=dnsip, alias=dnsalias, force=True)
            if vmentries:
                topentries = {}
                if scale is not None:
                    common.pprint("Applying scale", color='green')
                    scale = scale.split(',')
                    for s in scale:
                        s = s.split('=')
                        if len(s) == 2 and s[1].isdigit():
                            topentries[s[0]] = int(s[1])
                elif topologyfile is not None:
                    common.pprint("Processing Topology File %s..." % topologyfile, color='green')
                    topologyfile = os.path.expanduser(topologyfile)
                    if not os.path.exists(topologyfile):
                        common.pprint("Topology file %s not found.Ignoring...." % topologyfile, color='blue')
                    else:
                        with open(topologyfile, 'r') as topentries:
                            topentries = yaml.load(topentries)
                if topentries:
                    for entry in topentries:
                        if isinstance(topentries[entry], str) and not topentries[entry].isdigit():
                            continue
                        elif not isinstance(topentries[entry], int):
                            continue
                        number = int(topentries[entry])
                        if entry in [n[:-2] for n in vmentries]:
                            for i in range(1, number + 1):
                                newentry = "%s%0.2d" % (entry, i)
                                if newentry not in vmentries:
                                    entries[newentry] = entries["%s01" % entry]
                                    vmentries.append(newentry)
                common.pprint("Deploying Vms...", color='green')
                for name in vmentries:
                    profile = entries[name]
                    host = profile.get('host')
                    if host is None:
                        z = k
                    elif host in self.extraclients:
                        z = self.extraclients[host]
                    else:
                        common.pprint("Host %s not found. Using Default one" % host, color='blue')
                        z = k
                    if z.exists(name):
                        common.pprint("VM %s skipped!" % name, color='blue')
                        continue
                    if 'profile' in profile and profile['profile'] in vmprofiles:
                        customprofile = vmprofiles[profile['profile']]
                        profilename = profile['profile']
                    else:
                        customprofile = {}
                        profilename = 'kvirt'
                    pool = next((e for e in [profile.get('pool'), customprofile.get('pool'), self.pool] if e is not None))
                    template = next((e for e in [profile.get('template'), customprofile.get('template')] if e is not None), self.template)
                    cpumodel = next((e for e in [profile.get('cpumodel'), customprofile.get('cpumodel'), self.cpumodel] if e is not None))
                    cpuflags = next((e for e in [profile.get('cpuflags'), customprofile.get('cpuflags'), []] if e is not None))
                    numcpus = next((e for e in [profile.get('numcpus'), customprofile.get('numcpus'), self.numcpus] if e is not None))
                    memory = next((e for e in [profile.get('memory'), customprofile.get('memory'), self.memory] if e is not None))
                    disks = next((e for e in [profile.get('disks'), customprofile.get('disks'), self.disks] if e is not None))
                    disksize = next((e for e in [profile.get('disksize'), customprofile.get('disksize'), self.disksize] if e is not None))
                    diskinterface = next((e for e in [profile.get('diskinterface'), customprofile.get('diskinterface'), self.diskinterface] if e is not None))
                    diskthin = next((e for e in [profile.get('diskthin'), customprofile.get('diskthin'), self.diskthin] if e is not None))
                    guestid = next((e for e in [profile.get('guestid'), customprofile.get('guestid'), self.guestid] if e is not None))
                    vnc = next((e for e in [profile.get('vnc'), customprofile.get('vnc'), self.vnc] if e is not None))
                    cloudinit = next((e for e in [profile.get('cloudinit'), customprofile.get('cloudinit'), self.cloudinit] if e is not None))
                    reserveip = next((e for e in [profile.get('reserveip'), customprofile.get('reserveip'), self.reserveip] if e is not None))
                    reservedns = next((e for e in [profile.get('reservedns'), customprofile.get('reservedns'), self.reservedns] if e is not None))
                    reservehost = next((e for e in [profile.get('reservehost'), customprofile.get('reservehost'), self.reservehost] if e is not None))
                    report = next((e for e in [profile.get('report'), customprofile.get('report'), self.report] if e is not None))
                    nested = next((e for e in [profile.get('nested'), customprofile.get('nested'), self.nested] if e is not None))
                    start = next((e for e in [profile.get('start'), customprofile.get('start'), self.start] if e is not None))
                    nets = next((e for e in [profile.get('nets'), customprofile.get('nets'), self.nets] if e is not None))
                    iso = next((e for e in [profile.get('iso'), customprofile.get('iso')] if e is not None), self.iso)
                    keys = next((e for e in [profile.get('keys'), customprofile.get('keys'), self.keys] if e is not None))
                    # cmds = next((e for e in [profile.get('cmds'), customprofile.get('cmds'), self.cmds] if e is not None))
                    cmds = self.cmds + customprofile.get('cmds', []) + profile.get('cmds', [])
                    netmasks = next((e for e in [profile.get('netmasks'), customprofile.get('netmasks'), self.netmasks] if e is not None))
                    gateway = next((e for e in [profile.get('gateway'), customprofile.get('gateway')] if e is not None), self.gateway)
                    dns = next((e for e in [profile.get('dns'), customprofile.get('dns')] if e is not None), self.dns)
                    domain = next((e for e in [profile.get('domain'), customprofile.get('domain')] if e is not None), self.domain)
                    ips = profile.get('ips')
                    sharedkey = next((e for e in [profile.get('sharedkey'), customprofile.get('sharedkey'), self.sharedkey] if e is not None))
                    enableroot = next((e for e in [profile.get('enableroot'), customprofile.get('enableroot'), self.enableroot] if e is not None))
                    privatekey = next((e for e in [profile.get('privatekey'), customprofile.get('privatekey'), self.privatekey] if e is not None))
                    scripts = self.scripts + customprofile.get('scripts', []) + profile.get('scripts', [])
                    missingscript = False
                    if scripts:
                        scriptcmds = []
                        for script in scripts:
                            if '~' in script:
                                script = os.path.expanduser(script)
                            elif basedir != '':
                                script = "%s/%s" % (basedir, script)
                            if not os.path.exists(script):
                                common.pprint("Script %s not found. Ignoring this vm..." % script, color='red')
                                missingscript = True
                            else:
                                scriptlines = [Template(line.strip()).render() for line in open(script).readlines() if line != '\n']
                                if scriptlines:
                                    scriptcmds.extend(scriptlines)
                        if scriptcmds:
                            cmds = cmds + scriptcmds
                    if missingscript:
                        continue
                    if report:
                        reportcmd = ['curl -X POST -d "name=%s&status=OK&report=`cat /var/log/cloud-init.log`" %s/report' % (name, self.reporturl)]
                        if not cmds:
                            cmds = reportcmd
                        else:
                            cmds = cmds + reportcmd
                    files = next((e for e in [profile.get('files'), customprofile.get('files')] if e is not None), [])
                    if sharedkey:
                        if not os.path.exists("%s.key" % plan) or not os.path.exists("%s.key.pub" % plan):
                            os.popen("ssh-keygen -t rsa -N '' -f %s.key" % plan)
                        publickey = open("%s.key.pub" % plan).read().strip()
                        privatekey = open("%s.key" % plan).read().strip()
                        if keys is None:
                            keys = [publickey]
                        else:
                            keys.append(publickey)
                        if files:
                            files.append({'path': '/root/.ssh/id_rsa', 'content': privatekey})
                            files.append({'path': '/root/.ssh/id_rsa.pub', 'content': publickey})
                        else:
                            files = [{'path': '/root/.ssh/id_rsa', 'content': privatekey}, {'path': '/root/.ssh/id_rsa.pub', 'content': publickey}]
                    elif privatekey:
                        privatekeyfile = None
                        if os.path.exists("%s/.ssh/id_rsa" % os.environ['HOME']):
                            privatekeyfile = "%s/.ssh/id_rsa" % os.environ['HOME']
                        elif os.path.exists("%s/.ssh/id_rsa" % os.environ['HOME']):
                            privatekeyfile = "%s/.ssh/id_dsa" % os.environ['HOME']
                        if privatekeyfile is not None:
                            privatekey = open(privatekeyfile).read().strip()
                        if files:
                            files.append({'path': '/root/.ssh/id_rsa', 'content': privatekey})
                        else:
                            files = [{'path': '/root/.ssh/id_rsa', 'content': privatekey}]
                    result = z.create(name=name, plan=plan, profile=profilename, cpumodel=cpumodel, cpuflags=cpuflags, numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool, template=template, disks=disks, disksize=disksize, diskthin=diskthin, diskinterface=diskinterface, nets=nets, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit), reserveip=bool(reserveip), reservedns=bool(reservedns), reservehost=bool(reservehost), start=bool(start), keys=keys, cmds=cmds, ips=ips, netmasks=netmasks, gateway=gateway, dns=dns, domain=domain, nested=nested, tunnel=tunnel, files=files, enableroot=enableroot)
                    common.handle_response(result, name)
                    if result['result'] == 'success':
                        newvms.append(name)
                        common.lastvm(name)
                    ansible = next((e for e in [profile.get('ansible'), customprofile.get('ansible')] if e is not None), None)
                    if ansible is not None:
                        for element in ansible:
                            if 'playbook' not in element:
                                continue
                            playbook = element['playbook']
                            if 'variables' in element:
                                variables = element['variables']
                            if 'verbose' in element:
                                verbose = element['verbose']
                            else:
                                verbose = False
                            ansibleutils.play(z, name, playbook=playbook, variables=variables, verbose=verbose)
                    if delay > 0:
                        sleep(delay)
            if diskentries:
                common.pprint("Deploying Disks...", color='green')
            for disk in diskentries:
                profile = entries[disk]
                pool = profile.get('pool')
                vms = profile.get('vms')
                template = profile.get('template')
                size = int(profile.get('size', 10))
                if pool is None:
                    common.pprint("Missing Key Pool for disk section %s. Not creating it..." % disk, color='red')
                    continue
                if vms is None:
                    common.pprint("Missing or Incorrect Key Vms for disk section %s. Not creating it..." % disk, color='red')
                    continue
                if k.disk_exists(pool, disk):
                    common.pprint("Disk %s skipped!" % disk, color='blue')
                    continue
                if len(vms) > 1:
                    shareable = True
                else:
                    shareable = False
                newdisk = k.create_disk(disk, size=size, pool=pool, template=template, thin=False)
                common.pprint("Disk %s deployed!" % disk, color='green')
                for vm in vms:
                    k.add_disk(name=vm, size=size, pool=pool, template=template, shareable=shareable, existing=newdisk, thin=False)
            if containerentries:
                common.pprint("Deploying Containers...", color='green')
                label = "plan=%s" % (plan)
                for container in containerentries:
                    if dockerutils.exists_container(k, container):
                        common.pprint("Container %s skipped!" % container, color='blue')
                        continue
                    profile = entries[container]
                    if 'profile' in profile and profile['profile'] in containerprofiles:
                        customprofile = containerprofiles[profile['profile']]
                    else:
                        customprofile = {}
                    image = next((e for e in [profile.get('image'), profile.get('template'), customprofile.get('image'), customprofile.get('template')] if e is not None), None)
                    nets = next((e for e in [profile.get('nets'), customprofile.get('nets')] if e is not None), None)
                    ports = next((e for e in [profile.get('ports'), customprofile.get('ports')] if e is not None), None)
                    volumes = next((e for e in [profile.get('volumes'), profile.get('disks'), customprofile.get('volumes'), customprofile.get('disks')] if e is not None), None)
                    environment = next((e for e in [profile.get('environment'), customprofile.get('environment')] if e is not None), None)
                    cmd = next((e for e in [profile.get('cmd'), customprofile.get('cmd')] if e is not None), None)
                    common.pprint("Container %s deployed!" % container, color='green')
                    dockerutils.create_container(k, name=container, image=image, nets=nets, cmd=cmd, ports=ports, volumes=volumes, environment=environment, label=label)
            if ansibleentries:
                if not newvms:
                    common.pprint("Ansible skipped as no new vm within playbook provisioned", color='blue')
                    return
                for item, entry in enumerate(ansibleentries):
                    ansible = entries[ansibleentries[item]]
                    if 'playbook' not in ansible:
                        common.pprint("Missing Playbook for ansible.Ignoring...", color='red')
                        os._exit(1)
                    playbook = ansible['playbook']
                    if 'verbose' in ansible:
                        verbose = ansible['verbose']
                    else:
                        verbose = False
                    vms = []
                    if 'vms' in ansible:
                        vms = ansible['vms']
                        for vm in vms:
                            if vm not in newvms:
                                vms.remove(vm)
                    else:
                        vms = newvms
                    if not vms:
                        common.pprint("Ansible skipped as no new vm within playbook provisioned", color='blue')
                        return
                    ansibleutils.make_inventory(k, plan, newvms, tunnel=self.tunnel)
                    ansiblecommand = "ansible-playbook"
                    if verbose:
                        ansiblecommand = "%s -vvv" % ansiblecommand
                    ansibleconfig = os.path.expanduser('~/.ansible.cfg')
                    with open(ansibleconfig, "w") as f:
                        f.write("[ssh_connection]\nretries=10\n")
                    print("Running: %s -i /tmp/%s.inv %s" % (ansiblecommand, plan, playbook))
                    os.system("%s -i /tmp/%s.inv %s" % (ansiblecommand, plan, playbook))
        if ansible:
            common.pprint("Deploying Ansible Inventory...", color='green')
            if os.path.exists("/tmp/%s.inv" % plan):
                common.pprint("Inventory in /tmp/%s.inv skipped!" % (plan), color='blue')
            else:
                common.pprint("Creating ansible inventory for plan %s in /tmp/%s.inv" % (plan, plan), color='green')
                vms = []
                for vm in sorted(k.list()):
                    name = vm[0]
                    description = vm[4]
                    if description == plan:
                        vms.append(name)
                ansibleutils.make_inventory(k, plan, vms, tunnel=self.tunnel)
                return
        return {'result': 'success'}

    def handle_host(self, pool='default', template=None, switch=None, download=False, enable=False, disable=False, url=None, cmd=None):
        if download:
            k = self.k
            if pool is None:
                common.pprint("Missing pool.Leaving...", color='red')
                return {'result': 'failure', 'reason': "Missing pool"}
            if template is None:
                common.pprint("Missing template.Leaving...", color='red')
                return {'result': 'failure', 'reason': "Missing template"}
            common.pprint("Grabbing template %s..." % template, color='green')
            if url is None:
                url = TEMPLATES[template]
                template = os.path.basename(template)
                if not url.endswith('qcow2') and not url.endswith('img') and not url.endswith('qc2'):
                    if 'web' in sys.argv[0]:
                        return {'result': 'failure', 'reason': "Missing url"}
                    common.pprint("Opening url %s for you to grab complete url for %s" % (url, template), color='blue')
                    webbrowser.open(url, new=2, autoraise=True)
                    url = raw_input("Copy Url:\n")
                    if url.strip() == '':
                        common.pprint("Missing proper url.Leaving...", color='red')
                        return {'result': 'failure', 'reason': "Missing template"}
            if cmd is None and template in TEMPLATESCOMMANDS:
                cmd = TEMPLATESCOMMANDS[template]
            result = k.add_image(url, pool, cmd=cmd)
            common.handle_response(result, template, element='Template ', action='Added')
            # code = common.handle_response(result, shortname, element='Template ', action='Added')
            # os._exit(code)
            return {'result': 'success'}
        elif switch:
            if switch not in self.clients:
                common.pprint("Client %s not found in config.Leaving...." % switch, color='red')
                return {'result': 'failure', 'reason': "Client %s not found in config" % switch}
            enabled = self.ini[switch].get('enabled', True)
            if not enabled:
                common.pprint("Client %s is disabled.Leaving...." % switch, color='red')
                return {'result': 'failure', 'reason': "Client %s is disabled" % switch}
            common.pprint("Switching to client %s..." % switch, color='green')
            inifile = "%s/.kcli/config.yml" % os.environ.get('HOME')
            if os.path.exists(inifile):
                newini = ''
                for line in open(inifile).readlines():
                    if 'client' in line:
                        newini += " client: %s\n" % switch
                    else:
                        newini += line
                open(inifile, 'w').write(newini)
            return {'result': 'success'}
        elif enable:
            client = enable
            if client not in self.clients:
                common.pprint("Client %s not found in config.Leaving...." % client, color='green')
                return {'result': 'failure', 'reason': "Client %s not found in config" % client}
            common.pprint("Enabling client %s..." % client, color='green')
            inifile = "%s/.kcli/config.yml" % os.environ.get('HOME')
            if os.path.exists(inifile):
                newini = ''
                clientreached = False
                for line in open(inifile).readlines():
                    if line.startswith("%s:" % client):
                        clientreached = True
                        newini += line
                        continue
                    if clientreached and 'enabled' not in self.ini[client]:
                        newini += " enabled: true\n"
                        clientreached = False
                        newini += line
                        continue
                    elif clientreached and line.startswith(' enabled:'):
                        newini += " enabled: true\n"
                        clientreached = False
                    else:
                        newini += line
                open(inifile, 'w').write(newini)
            return {'result': 'success'}
        elif disable:
            client = disable
            if client not in self.clients:
                common.pprint("Client %s not found in config.Leaving...." % client, color='red')
                return {'result': 'failure', 'reason': "Client %s not found in config" % client}
            elif self.ini['default']['client'] == client:
                common.pprint("Client %s currently default.Leaving...." % client, color='red')
                return {'result': 'failure', 'reason': "Client %s currently default" % client}
            common.pprint("Disabling client %s..." % client, color='green')
            inifile = "%s/.kcli/config.yml" % os.environ.get('HOME')
            if os.path.exists(inifile):
                newini = ''
                clientreached = False
                for line in open(inifile).readlines():
                    if line.startswith("%s:" % client):
                        clientreached = True
                        newini += line
                        continue
                    if clientreached and 'enabled' not in self.ini[client]:
                        newini += " enabled: false\n"
                        clientreached = False
                        newini += line
                        continue
                    elif clientreached and line.startswith(' enabled:'):
                        newini += " enabled: false\n"
                        clientreached = False
                    else:
                        newini += line
                open(inifile, 'w').write(newini)
        return {'result': 'success'}

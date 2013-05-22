# -*- coding: utf8 -*-

from os.path import expanduser
from os.path import exists
from paramiko.config import SSHConfig
from exceptions import StormValueError


class StormConfig(SSHConfig):
    def parse(self, file_obj):
        """
        Read an OpenSSH config from the given file object.

        @param file_obj: a file-like object to read the config file from
        @type file_obj: file
        """
        host = {"host": ['*'], "config": {}}
        for line in file_obj:
            line = line.rstrip('\n').lstrip()
            #Comment handling. Ignore anything after 1st #
            line = line.split('#')[0]
            if (line == ''):
                continue
            if '=' in line:
                # Ensure ProxyCommand gets properly split
                if line.lower().strip().startswith('proxycommand'):
                    match = proxy_re.match(line)
                    key, value = match.group(1).lower(), match.group(2)
                else:
                    key, value = line.split('=', 1)
                    key = key.strip().lower()
            else:
                # find first whitespace, and split there
                i = 0
                while (i < len(line)) and not line[i].isspace():
                    i += 1
                if i == len(line):
                    raise Exception('Unparsable line: %r' % line)
                key = line[:i].lower()
                value = line[i:].lstrip()
            if key == 'host':
                self._config.append(host)
                value = value.split()
                host = {key: value, 'config': {}}
            #identityfile is a special case, since it is allowed to be
            # specified multiple times and they should be tried in order
            # of specification.
            elif key in ['identityfile', 'localforward', 'remoteforward']:
                if key in host['config']:
                    host['config'][key].append(value)
                else:
                    host['config'][key] = [value]
            elif key not in host['config']:
                host['config'].update({key: value})
        self._config.append(host)


class ConfigParser(object):
    """
    Config parser for ~/.ssh/config files.
    """

    def __init__(self, ssh_config_file=None):
        if not ssh_config_file:
            ssh_config_file = self.get_default_ssh_config_file()

        self.ssh_config_file = ssh_config_file

        if not exists(self.ssh_config_file):
            open(self.ssh_config_file, 'w+').close()

        self.config_data = []

    def get_default_ssh_config_file(self):
        return expanduser("~/.ssh/config")

    def load(self):
        config = StormConfig()

        config.parse(open(self.ssh_config_file))
        for entry in config.__dict__.get("_config"):
            for name in entry['host']:
                host_item = {
                    'host': name,
                        'options': entry.get("config"),
                }

                # minor bug in paramiko.SSHConfig that duplicates 
                #"Host *" entries.
                if entry.get("config") and len(entry.get("config")) > 0:
                    self.config_data.append(host_item)

        return self.config_data

    def add_host(self, host, options):
        self.config_data.append({
            'host': host,
            'options': options,
        })

        return self

    def update_host(self, host, options):
        for index, host_entry in enumerate(self.config_data):
            if host_entry.get("host") == host:
                self.config_data[index]["options"] = options

        return self

    def delete_host(self, host):
        found = 0
        for index, host_entry in enumerate(self.config_data):
            if host_entry.get("host") == host:
                del self.config_data[index]
                found += 1

        if found == 0:
            raise StormValueError('No host found')
        return self

    def delete_all_hosts(self):
        self.config_data = []
        self.write_to_ssh_config()

        return self

    def dump(self):
        if len(self.config_data) < 1:
            return

        file_content = ""
        for host_item in self.config_data:
            host_item_content = "Host {0}\n".format(host_item.get("host"))
            for key, value in host_item.get("options").iteritems():
                if isinstance(value, list):
                    sub_content = ""
                    for value_ in value:
                        sub_content += "    {0} {1}\n".format(
                            key, value_
                        )
                    host_item_content += sub_content
                else:
                    host_item_content += "    {0} {1}\n".format(
                        key, value
                    )
            file_content += host_item_content

        return file_content

    def write_to_ssh_config(self):
        f = open(self.ssh_config_file, 'w+')
        data = self.dump()
        if data:
            f.write(data)
        f.close()

        return self

#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# (c) 2018, Ansible by Red Hat, inc
#
# This file is part of Ansible by Red Hat
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import (absolute_import, division, print_function)
from ansible.module_utils.network.asa.asa import get_config
__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: asa_facts
version_added: "2.6"
author: "Stefan Schlesinger <@sts>"
short_description: Collect facts from remote devices running Cisco ASA
description:
  - Collects a base set of device facts from a remote device that
    is running Cisco ASA.  This module prepends all of the
    base network fact keys with C(ansible_net_<fact>).  The facts
    module will always collect a base set of facts from the device
    and can enable or disable collection of additional facts.
extends_documentation_fragment: asa
notes:
  - Tested against ASA 5510 9.1(7)29
options:
  gather_subset:
    description:
      - When supplied, this argument will restrict the facts collected
        to a given subset.  Possible values for this argument include
        all, hardware, config, failover and interfaces.  Can specify a
        list of values to include a larger subset.  Values can also be
        used with an initial C(M(!)) to specify that a specific subset
        should not be collected.
    required: false
    default: '!config'
"""

EXAMPLES = """
- name: Collect all facts from the device
  asa_facts:
    gather_subset: all
- name: Collect only the config and default facts
  asa_facts:
    gather_subset:
      - config
- name: Do not collect hardware facts
  asa_facts:
    gather_subset:
      - "!hardware"
"""

RETURN = """
ansible_net_gather_subset:
  description: The list of fact subsets collected from the device
  returned: always
  type: list
# default
ansible_net_model:
  description: The model name returned from the device
  returned: always
  type: string
ansible_net_serialnum:
  description: The serial number of the remote device
  returned: always
  type: string
ansible_net_version:
  description: The operating system version running on the remote device
  returned: always
  type: string
ansible_net_asdm_version:
  description: The ASA security device manager running on the remote device
  returned: always
  type: string
ansible_net_asdm_image:
  description: The image file of the ASA security device manager
  returned: always
  type: string
ansible_net_asdm_image_configured
  description: The currently configured image file of the ASA security device manager
  returned: when asdm image is configured
  type: string
ansible_net_hostname:
  description: The configured hostname of the device
  returned: always
  type: string
ansible_net_image:
  description: The boot image file the device is running
  returned: always
  type: string
ansible_net_boot_images_configured:
  description: A list of boot images configured in running configuration
  returned: when boot images are configured
  type: array
# hardware
ansible_net_filesystems:
  description: All file system names available on the device
  returned: when hardware is configured
  type: list
# config
ansible_net_config:
  description: The current active config from the device
  returned: when config is configured
  type: string
# interfaces
ansible_net_interfaces:
  description: A hash of all interfaces running on the system
  returned: when interfaces is configured
  type: dict
# failover
ansible_net_failover_role
  description: The current failover role of the system, either Primary or Secondary
  returned: when failover is enabled
  type: string
ansible_net_failover_state
  description:
  - The current failover role of the system, usually either Active
    or Standby Ready. A complete list of states is available in the Cisco ASA
    Series Command Reference.
  returned: when failover is enabled
  type: string
ansible_net_failover_partner_role
  description: See ansible_net_failover_role, but for the other/partner device in the cluster.
  returned: when failover is enabled
  type: string
ansible_net_failover_partner_state
  description: See ansible_net_failover_state, but for the other/partner device in the cluster.
  returned: when failover is enabled
  type: string
"""

import re

from ansible.module_utils.network.asa.asa import run_commands
from ansible.module_utils.network.asa.asa import asa_argument_spec, check_args
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import iteritems


class FactsBase(object):

    COMMANDS = list()

    def __init__(self, module):
        self.module = module
        self.facts = dict()
        self.responses = None

    def populate(self):
        self.responses = run_commands(self.module, commands=self.COMMANDS, check_rc=False)

    def run(self, cmd):
        return run_commands(self.module, commands=cmd, check_rc=False)


class Default(FactsBase):

    COMMANDS = [
      'show version',
      'show asdm image',
    ]

    def populate(self):
        super(Default, self).populate()
        data = self.responses[0]
        if data:
            self.facts['version'] = self.parse_version(data)
            self.facts['hostname'] = self.parse_hostname(data)
            self.facts['model'] = self.parse_model(data)
            self.facts['image'] = self.parse_image(data)
            self.facts['serialnum'] = self.parse_serialnum(data)
            self.facts['asdm_version'] = self.parse_asdm_version(data)
            self.facts['asdm_image'] = self.parse_asdm_image(self.responses[1])
            self.parse_stacks(data)

    def parse_version(self, data):
        match = re.search(r'Version (\S+?)(?:,\s|\s)', data)
        if match:
            return match.group(1)

    def parse_hostname(self, data):
        match = re.search(r'^(.+) up', data, re.M)
        if match:
            return match.group(1)

    def parse_model(self, data):
        match = re.search(r'Hardware:\s+(\w+), ', data)
        if match:
            return match.group(1)

    def parse_image(self, data):
        match = re.search(r'image file is "(.+)"', data)
        if match:
            return match.group(1)

    def parse_serialnum(self, data):
        match = re.search(r'Serial Number: (\S+)', data)
        if match:
            return match.group(1)

    def parse_asdm_version(self, data):
        match = re.search(r'Device Manager Version (\S+)', data)
        if match:
            return match.group(1)

    def parse_asdm_image(self, data):
        match = re.search(r'Device Manager image file, (.+)', data)
        if match:
            return match.group(1)

    def parse_stacks(self, data):
        match = re.findall(r'^Model number\s+: (\S+)', data, re.M)
        if match:
            self.facts['stacked_models'] = match

        match = re.findall(r'^System serial number\s+: (\S+)', data, re.M)
        if match:
            self.facts['stacked_serialnums'] = match

class Failover(FactsBase):

    COMMANDS = [
      'show failover',
    ]

    def populate(self):
        super(Failover, self).populate()
        data = self.responses[0]
        if data:
            self.facts['failover'] = self.parse_failover_available(data)
            self.parse_state(data)

    def parse_failover_available(self, data):
        match = re.search(r'Failover On', data)
        if match:
            return True
        return False

    def parse_state(self, data):
        # Cisco ASA states documentation available at
        # https://www.cisco.com/c/en/us/td/docs/security/asa/asa-command-reference/S/cmdref3/s7.html#pgfId-1634344
        match = re.search(r'This host:\s+(Primary|Secondary) - (.+)', data)
        if match:
            self.facts['failover_role'] = match.group(1)
            self.facts['failover_state'] = match.group(2).strip()

        match = re.search(r'Other host:\s+(Primary|Secondary) - (.+)', data)
        if match:
            self.facts['failover_partner_role'] = match.group(1)
            self.facts['failover_partner_state'] = match.group(2).strip()

class Hardware(FactsBase):

    COMMANDS = [
        'dir'
    ]

    def populate(self):
        super(Hardware, self).populate()
        data = self.responses[0]
        if data:
            self.facts['filesystems'] = self.parse_filesystems(data)

    def parse_filesystems(self, data):
        return re.findall(r'^Directory of (\S+)/', data, re.M)


class Config(FactsBase):

    def populate(self):
        super(Config, self).populate()
        data = get_config(self.module)
        if data:
            #self.facts['config'] = data
            self.facts['boot_images_configured'] = self.parse_configured_boot_images(data)
            self.facts['asdm_image_configured'] = self.parse_configured_asdm_image(data)

    def parse_configured_boot_images(self, data):
        match = re.findall(r'boot system (.+)', data, re.M)
        if match:
            return match

    def parse_configured_asdm_image(self, data):
        match = re.search(r'asdm image (.+)', data)
        if match:
            return match.group(1)

class Interfaces(FactsBase):

    COMMANDS = [
        'show interface',
        'show ipv6 interface brief'
    ]

    def populate(self):
        super(Interfaces, self).populate()

        data = self.responses[0]
        if data:
            interfaces = self.parse_interfaces(data)
            self.facts['interfaces'] = self.populate_interfaces(interfaces)

    def populate_interfaces(self, interfaces):
        facts = dict()
        for key, value in iteritems(interfaces):
            intf = dict()
            intf['description'] = self.parse_description(value)
            intf['macaddress'] = self.parse_macaddress(value)
            intf['mtu'] = self.parse_mtu(value)
            intf['lineprotocol'] = self.parse_lineprotocol(value)
            intf['operstatus'] = self.parse_operstatus(value)
            intf['interface-type'] = self.parse_type(value)
            intf['ipv4_addr'] = self.parse_ipv4_addr(value)
            intf['ipv4_subnet'] = self.parse_ipv4_subnet(value)

            facts[key] = intf
        return facts

    def parse_interfaces(self, data):
        parsed = dict()
        key = ''
        for line in data.split('\n'):
            if len(line) == 0:
                continue
            elif (line[0] == '\t') or (line[0] == ' '):
                parsed[key] += '\n%s' % line
            else:
                match = re.match(r'^(?=.*\bInterface\b)(?:\S+ )(\S+)', line)
                if match:
                    key = match.group(1)
                    parsed[key] = re.match(r'^(?=.*\bInterface\b)(?:\S+ )(.*\S+)', line).group(1)
        return parsed

    def parse_ipv4_addr(self, data):
        match = re.search(r'IP address (.+),', data)
        if match:
            return match.group(1)

    def parse_ipv4_subnet(self, data):
        match = re.search(r'subnet mask (.+)', data)
        if match:
            return match.group(1)

    def parse_description(self, data):
        match = re.search(r'Description: (.+)$', data, re.M)
        if match:
            return match.group(1)
        else:
            return "not set"

    def parse_macaddress(self, data):
        match = re.search(r'MAC address (.+),', data)
        if match:
            return match.group(1)

    def parse_mtu(self, data):
        match = re.search(r'MTU (\S+)', data)
        if match:
            return match.group(1)

    def parse_type(self, data):
        match = re.search(r'Hardware is (.+),', data, re.M)
        if match:
            return match.group(1)

    def parse_lineprotocol(self, data):
        match = re.search(r'line protocol is (.+)$', data, re.M)
        if match:
            return match.group(1)

    def parse_operstatus(self, data):
        match = re.search(r'^(?:.+) is (.+),', data, re.M)
        if match:
            return match.group(1)

FACT_SUBSETS = dict(
    default=Default,
    hardware=Hardware,
    interfaces=Interfaces,
    config=Config,
    failover=Failover
)

VALID_SUBSETS = frozenset(FACT_SUBSETS.keys())

global warnings
warnings = list()

def main():
    """main entry point for module execution
    """
    argument_spec = dict(
        gather_subset=dict(default='!config', type='list')
    )

    argument_spec.update(asa_argument_spec)

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    check_args(module)

    gather_subset = module.params['gather_subset']

    runable_subsets = set()
    exclude_subsets = set()

    for subset in gather_subset:
        if subset == 'all':
            runable_subsets.update(VALID_SUBSETS)
            continue

        if subset.startswith('!'):
            subset = subset[1:]
            if subset == 'all':
                exclude_subsets.update(VALID_SUBSETS)
                continue
            exclude = True
        else:
            exclude = False

        if subset not in VALID_SUBSETS:
            module.fail_json(msg='Bad subset')

        if exclude:
            exclude_subsets.add(subset)
        else:
            runable_subsets.add(subset)

    if not runable_subsets:
        runable_subsets.update(VALID_SUBSETS)

    runable_subsets.difference_update(exclude_subsets)
    runable_subsets.add('default')

    facts = dict()
    facts['gather_subset'] = list(runable_subsets)

    instances = list()
    for key in runable_subsets:
        instances.append(FACT_SUBSETS[key](module))

    for inst in instances:
        inst.populate()
        facts.update(inst.facts)

    ansible_facts = dict()
    for key, value in iteritems(facts):
        key = 'ansible_net_%s' % key
        ansible_facts[key] = value

    module.exit_json(ansible_facts=ansible_facts, warnings=warnings)

if __name__ == '__main__':
    main()

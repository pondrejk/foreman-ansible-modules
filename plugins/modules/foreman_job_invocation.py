#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2020 Peter Ondrejka <pondrejk@redhat.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: foreman_job_invocation
short_description: Manage Job Invocations in Foreman
description:
  - "Manage Foreman Remote Execution Job Invocations"
author:
  - "Peter Ondrejka (@pondrejk)"
options:

extends_documentation_fragment:
  - foreman
  - foreman.entity_state_with_defaults
  - foreman.taxonomy
'''

EXAMPLES = '''

- name: "Create a Job Invocation"
  foreman_job_invocation:
    username: "admin"
    password: "changeme"
    server_url: "https://foreman.example.com"
    name: A New Job Template
    state: present
    template: |
      <%#
          name: A Job Template
      %>
      rm -rf <%= input("toDelete") %>
    template_inputs:
      - name: toDelete
        input_type: user
    locations:
    - Gallifrey
    organizations:
    - TARDIS INC

'''

RETURN = ''' # '''

import os
from ansible.module_utils.foreman_helper import (
    ForemanEntityAnsibleModule,
)

ssh_foreman_spec = {
        'effective_user': dict(),
}

recurrnece_foreman_spec = {
        'cron_line': dict(),
        'max_iteration': dict(),
        'end_time': dict(),
}

scheduling_foreman_spec = {
        'start_at': dict(),
        'start_before': dict(),
}

concurrency_control_foreman_spec = {
        'life_span': dict(),
        'concurrency_level': dict(),
}


class ForemanJobInvocationModule(ForemanEntityAnsibleModule):
    pass


def main():
    module = ForemanJobInvocationModule(
        foreman_spec=dict(
            search_query=dict(),
            bookmark_id=dict(),
            job_template_id=dict(required=true),
            targeting_type=dict(default='static_query', choices=['static_query', 'dynamic_query']),
            randomized_ordering=dict(type='bool', default=False),
            feature=dict(),
            execution_timeout_interval=dict(),
            locked=dict(type='bool', default=False),
            ssh=dict(type='nested_list', foreman_spec=ssh_foreman_spec),
            recurrence=dict(type='nested_list', foreman_spec=recurrnece_foreman_spec),
            scheduling=dict(type='nested_list', foreman_spec=scheduling_foreman_spec),
            concurrency_control=dict(type='nested_list', foreman_spec=concurrency_control_foreman_spec),
        ),
    )

    # make sure we have a search query
    if 'search_query' and 'booknark_id' not in module.foreman_params:
        module.fail_json(
            msg='No search query specified and no bookmark to infer it.')

    with module.api_connection():
        module.run()

if __name__ == '__main__':
    main()

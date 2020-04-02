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

- name: "Create a Job Template inline"
  foreman_job_template:
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
            job_template_id=dict(required=true),
            targeting_type=dict(default='static_query', choices=['static_query', 'dynamic_query']),
            randomized_ordering=dict(type='bool', default=False),
            search_query=dict(),
            feature=dict(),
            execution_timeout_interval=dict(),
            locked=dict(type='bool', default=False),
            ssh=dict(type='nested_list', foreman_spec=ssh_foreman_spec),
            recurrence=dict(type='nested_list', foreman_spec=recurrnece_foreman_spec),
            scheduling=dict(type='nested_list', foreman_spec=scheduling_foreman_spec),
            concurrency_control=dict(type='nested_list', foreman_spec=concurrency_control_foreman_spec),
        ),

    )

    # We do not want a layout text for bulk operations
    if module.foreman_params.get('name') == '*':
        {if module.foreman_params.get('file_name') or module.foreman_params.get('template'):
            module.fail_json(
                msg="Neither file_name nor template allowed if 'name: *'!")

    entity = None
    file_name = module.foreman_params.pop('file_name', None)

    if file_name or 'template' in module.foreman_params:
        if file_name:
            parsed_dict = parse_template_from_file(file_name, module)
        else:
            parsed_dict = parse_template(module.foreman_params['template'], module)
        # sanitize name from template data
        # The following condition can actually be hit, when someone is trying to import a
        # template with the name set to '*'.
        # Besides not being sensible, this would go horribly wrong in this module.
        if parsed_dict.get('name') == '*':
            module.fail_json(msg="Cannot use '*' as a job template name!")
        # module params are priorized
        parsed_dict.update(module.foreman_params)
        # make sure certain values are set
        module.foreman_params = template_defaults.copy()
        module.foreman_params.update(parsed_dict)

    # make sure, we have a name
    if 'name' not in module.foreman_params:
        if file_name:
            module.foreman_params['name'] = os.path.splitext(
                os.path.basename(file_name))[0]
        else:
            module.fail_json(
                msg='No name specified and no filename to infer it.')

    affects_multiple = module.foreman_params['name'] == '*'
    # sanitize user input, filter unuseful configuration combinations with 'name: *'
    if affects_multiple:
        if module.state == 'present_with_defaults':
            module.fail_json(msg="'state: present_with_defaults' and 'name: *' cannot be used together")
        if module.desired_absent:
            further_params = set(module.foreman_params.keys()) - {'name', 'entity'}
            if further_params:
                module.fail_json(msg='When deleting all job templates, there is no need to specify further parameters: %s ' % further_params)

    with module.api_connection():
        if 'audit_comment' in module.foreman_params:
            extra_params = {'audit_comment': module.foreman_params['audit_comment']}
        else:
            extra_params = {}

        if affects_multiple:
            module.set_entity('entity', None)  # prevent lookup
            entities = module.list_resource('job_templates')
            if not entities:
                # Nothing to do; shortcut to exit
                module.exit_json()
            if not module.desired_absent:  # not 'thin'
                entities = [module.show_resource('job_templates', entity['id']) for entity in entities]
                module.auto_lookup_entities()
            module.foreman_params.pop('name')
            for entity in entities:
                module.ensure_entity('job_templates', module.foreman_params, entity, params=extra_params)
        else:
            # The name could have been determined to late, so copy it again
            module.foreman_params['entity'] = module.foreman_params['name']
            entity = module.lookup_entity('entity')
            # TemplateInputs need to be added as separate entities later
            template_inputs = module.foreman_params.get('template_inputs')

            job_template = module.run(params=extra_params)

            update_dependent_entities = (module.state == 'present' or (module.state == 'present_with_defaults' and module.changed))
            if update_dependent_entities and template_inputs is not None:
                scope = {'template_id': job_template['id']}

                # Manage TemplateInputs here
                current_template_input_list = module.list_resource('template_inputs', params=scope) if entity else []
                current_template_inputs = {item['name']: item for item in current_template_input_list}
                for template_input_dict in template_inputs:
                    template_input_dict = {key: value for key, value in template_input_dict.items() if value is not None}

                    template_input_entity = current_template_inputs.pop(template_input_dict['name'], None)

                    module.ensure_entity(
                        'template_inputs', template_input_dict, template_input_entity,
                        params=scope, foreman_spec=template_input_foreman_spec,
                    )

                # At this point, desired template inputs have been removed from the dict.
                for template_input_entity in current_template_inputs.values():
                    module.ensure_entity(
                        'template_inputs', None, template_input_entity, state="absent",
                        params=scope, foreman_spec=template_input_foreman_spec,
                    )


if __name__ == '__main__':
    main()

import json

from .test_workflows import BaseWorkflowsApiTestCase

from .yaml_to_workflow import yaml_to_workflow


class WorkflowsFromYamlApiTestCase( BaseWorkflowsApiTestCase ):

    def setUp( self ):
        super( WorkflowsFromYamlApiTestCase, self ).setUp()

    def test_simple_upload(self):
        workflow_id = self.__upload_yaml("""
- type: input
- tool_id: cat1
  state:
    input1:
      $link: 0
- tool_id: cat1
  state:
    input1:
      $link: 1#out_file1
- tool_id: random_lines1
  state:
    num_lines: 10
    input:
      $link: 2#out_file1
    seed_source:
      seed_source_selector: set_seed
      seed: asdf
      __current_case__: 1
""")
        self._get("workflows/%s/download" % workflow_id).content

    def __upload_yaml(self, has_yaml):
        workflow = yaml_to_workflow(has_yaml)
        workflow_str = json.dumps(workflow, indent=4)
        print workflow_str
        data = {
            'workflow': workflow_str
        }
        upload_response = self._post( "workflows", data=data )
        self._assert_status_code_is( upload_response, 200 )
        self._assert_user_has_workflow_with_name( "%s (imported from API)" % ( workflow[ "name" ] ) )
        return upload_response.json()[ "id" ]

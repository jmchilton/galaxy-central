import functools
from json import dumps, loads
import operator

from .helpers import skip_without_tool
from .helpers import wait_on_state
from .test_workflows import BaseWorkflowsApiTestCase
import yaml


class WorkflowExtractionApiTestCase( BaseWorkflowsApiTestCase ):

    def setUp( self ):
        super( WorkflowExtractionApiTestCase, self ).setUp()
        self.history_id = self.dataset_populator.new_history()

    @skip_without_tool( "cat1" )
    def test_extract_from_history( self ):
        # Run the simple test workflow and extract it back out from history
        cat1_job_id = self.__setup_and_run_cat1_workflow( history_id=self.history_id )
        contents = self._history_contents()
        input_hids = map( lambda c: c[ "hid" ], contents[ 0:2 ] )
        downloaded_workflow = self._extract_and_download_workflow(
            dataset_ids=input_hids,
            job_ids=[ cat1_job_id ],
        )
        self.assertEquals( downloaded_workflow[ "name" ], "test import from history" )
        self.__assert_looks_like_cat1_example_workflow( downloaded_workflow )

    def test_extract_with_copied_inputs( self ):
        old_history_id = self.dataset_populator.new_history()
        # Run the simple test workflow and extract it back out from history
        self.__setup_and_run_cat1_workflow( history_id=old_history_id )

        # Bug cannot mess up hids or these don't extract correctly. See Trello card here:
        # https://trello.com/c/mKzLbM2P
        # # create dummy dataset to complicate hid mapping
        # self.dataset_populator.new_dataset( history_id, content="dummydataset" )
        # offset = 1

        offset = 0
        old_contents = self._history_contents( old_history_id )
        for old_dataset in old_contents:
            self.__copy_content_to_history( self.history_id, old_dataset )
        new_contents = self._history_contents()
        input_hids = map( lambda c: c[ "hid" ], new_contents[ (offset + 0):(offset + 2) ] )
        cat1_job_id = self.__job_id( self.history_id, new_contents[ (offset + 2) ][ "id" ] )
        downloaded_workflow = self._extract_and_download_workflow(
            dataset_ids=input_hids,
            job_ids=[ cat1_job_id ],
        )
        self.__assert_looks_like_cat1_example_workflow( downloaded_workflow )

    @skip_without_tool( "random_lines1" )
    def test_extract_mapping_workflow_from_history( self ):
        hdca, job_id1, job_id2 = self.__run_random_lines_mapped_over_pair( self.history_id )
        downloaded_workflow = self._extract_and_download_workflow(
            dataset_collection_ids=[ hdca[ "hid" ] ],
            job_ids=[ job_id1, job_id2 ],
        )
        self.__assert_looks_like_randomlines_mapping_workflow( downloaded_workflow )

    def test_extract_copied_mapping_from_history( self ):
        old_history_id = self.dataset_populator.new_history()
        hdca, job_id1, job_id2 = self.__run_random_lines_mapped_over_pair( old_history_id )

        old_contents = self._history_contents( old_history_id )
        for old_content in old_contents:
            self.__copy_content_to_history( self.history_id, old_content )
        # API test is somewhat contrived since there is no good way
        # to retrieve job_id1, job_id2 like this for copied dataset
        # collections I don't think.
        downloaded_workflow = self._extract_and_download_workflow(
            dataset_collection_ids=[ hdca[ "hid" ] ],
            job_ids=[ job_id1, job_id2 ],
        )
        self.__assert_looks_like_randomlines_mapping_workflow( downloaded_workflow )

    @skip_without_tool( "random_lines1" )
    @skip_without_tool( "multi_data_param" )
    def test_extract_reduction_from_history( self ):
        hdca = self.dataset_collection_populator.create_pair_in_history( self.history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"] ).json()
        hdca_id = hdca[ "id" ]
        inputs1 = {
            "input": { "batch": True, "values": [ { "src": "hdca", "id": hdca_id } ] },
            "num_lines": 2
        }
        implicit_hdca1, job_id1 = self._run_tool_get_collection_and_job_id( self.history_id, "random_lines1", inputs1 )
        inputs2 = {
            "f1": { "src": "hdca", "id": implicit_hdca1[ "id" ] },
            "f2": { "src": "hdca", "id": implicit_hdca1[ "id" ] },
        }
        reduction_run_output = self.dataset_populator.run_tool(
            tool_id="multi_data_param",
            inputs=inputs2,
            history_id=self.history_id,
        )
        job_id2 = reduction_run_output[ "jobs" ][ 0 ][ "id" ]
        self.dataset_populator.wait_for_history( self.history_id, assert_ok=True, timeout=20 )
        downloaded_workflow = self._extract_and_download_workflow(
            dataset_collection_ids=[ hdca[ "hid" ] ],
            job_ids=[ job_id1, job_id2 ],
        )
        assert len( downloaded_workflow[ "steps" ] ) == 3
        collect_step_idx = self._assert_first_step_is_paired_input( downloaded_workflow )
        tool_steps = self._get_steps_of_type( downloaded_workflow, "tool", expected_len=2 )
        random_lines_map_step = tool_steps[ 0 ]
        reduction_step = tool_steps[ 1 ]
        random_lines_input = random_lines_map_step[ "input_connections" ][ "input" ]
        assert random_lines_input[ "id" ] == collect_step_idx
        reduction_step_input = reduction_step[ "input_connections" ][ "f1" ]
        assert reduction_step_input[ "id"] == random_lines_map_step[ "id" ]

    @skip_without_tool( "collection_paired_test" )
    def test_extract_workflows_with_dataset_collections( self ):
        hdca = self.dataset_collection_populator.create_pair_in_history( self.history_id ).json()
        hdca_id = hdca[ "id" ]
        inputs = {
            "f1": dict( src="hdca", id=hdca_id )
        }
        run_output = self.dataset_populator.run_tool(
            tool_id="collection_paired_test",
            inputs=inputs,
            history_id=self.history_id,
        )
        job_id = run_output[ "jobs" ][ 0 ][ "id" ]
        self.dataset_populator.wait_for_history( self.history_id, assert_ok=True )
        downloaded_workflow = self._extract_and_download_workflow(
            dataset_collection_ids=[ hdca[ "hid" ] ],
            job_ids=[ job_id ],
        )
        collection_steps = self._get_steps_of_type( downloaded_workflow, "data_collection_input", expected_len=1 )
        collection_step = collection_steps[ 0 ]
        collection_step_state = loads( collection_step[ "tool_state" ] )
        self.assertEquals( collection_step_state[ "collection_type" ], u"paired" )

    def test_extract_workflow_with_output_collections( self ):
        history_id = self._run_jobs("""
steps:
  - label: text_input1
    type: input
  - label: text_input2
    type: input
  - label: cat_inputs
    tool_id: cat1
    state:
      input1:
        $link: text_input1
      queries:
        - input2:
            $link: text_input2
  - label: split_up
    tool_id: collection_split_on_column
    state:
      input1:
        $link: cat_inputs#out_file1
  - tool_id: cat_list
    state:
      input1:
        $link: split_up#split_output
test_data:
  text_input1: "samp1\t10.0\nsamp2\t20.0\n"
  text_input2: "samp1\t30.0\nsamp2\t40.0\n"
""")
        jobs = self._history_jobs( history_id )
        job_ids = map( functools.partial(self._job_id_for_tool, jobs ), [ "cat1", "collection_split_on_column", "cat_list" ] )
        downloaded_workflow = self._extract_and_download_workflow(
            dataset_ids=[ "1", "2" ],
            job_ids=job_ids,
        )
        print downloaded_workflow
        assert False

    def _run_jobs( self, jobs_yaml ):
        history_id = self.history_id
        workflow_id = self._upload_yaml_workflow(
            jobs_yaml
        )
        jobs_descriptions = yaml.load( jobs_yaml )
        test_data = jobs_descriptions["test_data"]

        label_map = {}
        for key, value in test_data.items():
            hda = self.dataset_populator.new_dataset( history_id, content=value )
            workflow_request = dict(
                history="hist_id=%s" % history_id,
                workflow_id=workflow_id,
            )
            label_map[key] = self._ds_entry( hda )
        workflow_request[ "inputs" ] = dumps( label_map )
        workflow_request[ "inputs_by" ] = 'name'
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        url = "workflows/%s/usage" % ( workflow_id )
        invocation_response = self._post( url, data=workflow_request )
        self._assert_status_code_is( invocation_response, 200 )
        invocation = invocation_response.json()
        invocation_id = invocation[ "id" ]
        # Wait for workflow to become fully scheduled and then for all jobs
        # complete.
        self.wait_for_invocation( workflow_id, invocation_id )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        return history_id

    def wait_for_invocation( self, workflow_id, invocation_id ):
        url = "workflows/%s/usage/%s" % ( workflow_id, invocation_id )
        return wait_on_state( lambda: self._get( url )  )

    def _history_jobs( self, history_id ):
        return self._get("jobs", { "history_id": history_id } ).json()

    def _job_id_for_tool( self, jobs, tool_id ):
        return self._job_for_tool( jobs, tool_id )[ "id" ]

    def _job_for_tool( self, jobs, tool_id ):
        tool_jobs = filter( lambda j: j["tool_id"] == tool_id, jobs )
        if not tool_jobs:
            assert False, "Failed to find job for tool %s" % tool_id
        if len( tool_jobs ) > 1:
            assert False, "Found multiple jobs for tool %s" % tool_id
        return tool_jobs[ 0 ]

    def __run_random_lines_mapped_over_pair( self, history_id ):
        hdca = self.dataset_collection_populator.create_pair_in_history( history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"] ).json()
        hdca_id = hdca[ "id" ]
        inputs1 = {
            "input": { "batch": True, "values": [ { "src": "hdca", "id": hdca_id } ] },
            "num_lines": 2
        }
        implicit_hdca1, job_id1 = self._run_tool_get_collection_and_job_id( history_id, "random_lines1", inputs1 )
        inputs2 = {
            "input": { "batch": True, "values": [ { "src": "hdca", "id": implicit_hdca1[ "id" ] } ] },
            "num_lines": 1
        }
        _, job_id2 = self._run_tool_get_collection_and_job_id( history_id, "random_lines1", inputs2 )
        return hdca, job_id1, job_id2

    def __assert_looks_like_randomlines_mapping_workflow( self, downloaded_workflow ):
        # Assert workflow is input connected to a tool step with one output
        # connected to another tool step.
        assert len( downloaded_workflow[ "steps" ] ) == 3
        collect_step_idx = self._assert_first_step_is_paired_input( downloaded_workflow )
        tool_steps = self._get_steps_of_type( downloaded_workflow, "tool", expected_len=2 )
        tool_step_idxs = []
        tool_input_step_idxs = []
        for tool_step in tool_steps:
            self._assert_has_key( tool_step[ "input_connections" ], "input" )
            input_step_idx = tool_step[ "input_connections" ][ "input" ][ "id" ]
            tool_step_idxs.append( tool_step[ "id" ] )
            tool_input_step_idxs.append( input_step_idx )

        assert collect_step_idx not in tool_step_idxs
        assert tool_input_step_idxs[ 0 ] == collect_step_idx
        assert tool_input_step_idxs[ 1 ] == tool_step_idxs[ 0 ]

    def __assert_looks_like_cat1_example_workflow( self, downloaded_workflow ):
        assert len( downloaded_workflow[ "steps" ] ) == 3
        input_steps = self._get_steps_of_type( downloaded_workflow, "data_input", expected_len=2 )
        tool_step = self._get_steps_of_type( downloaded_workflow, "tool", expected_len=1 )[ 0 ]

        input1 = tool_step[ "input_connections" ][ "input1" ]
        input2 = tool_step[ "input_connections" ][ "queries_0|input2" ]

        self.assertEquals( input_steps[ 0 ][ "id" ], input1[ "id" ] )
        self.assertEquals( input_steps[ 1 ][ "id" ], input2[ "id" ] )

    def _history_contents( self, history_id=None ):
        if history_id is None:
            history_id = self.history_id
        return self._get( "histories/%s/contents" % history_id ).json()

    def __copy_content_to_history( self, history_id, content ):
        if content[ "history_content_type" ] == "dataset":
            payload = dict(
                source="hda",
                content=content["id"]
            )
            response = self._post( "histories/%s/contents/datasets" % history_id, payload )

        else:
            payload = dict(
                source="hdca",
                content=content["id"]
            )
            response = self._post( "histories/%s/contents/dataset_collections" % history_id, payload )
        self._assert_status_code_is( response, 200 )
        return response.json()

    def __setup_and_run_cat1_workflow( self, history_id ):
        workflow = self.workflow_populator.load_workflow( name="test_for_extract" )
        workflow_request, history_id = self._setup_workflow_run( workflow, history_id=history_id )
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )

        self.dataset_populator.wait_for_history( history_id, assert_ok=True, timeout=10 )
        return self.__cat_job_id( history_id )

    def _assert_first_step_is_paired_input( self, downloaded_workflow ):
        collection_steps = self._get_steps_of_type( downloaded_workflow, "data_collection_input", expected_len=1 )
        collection_step = collection_steps[ 0 ]
        collection_step_state = loads( collection_step[ "tool_state" ] )
        self.assertEquals( collection_step_state[ "collection_type" ], u"paired" )
        collect_step_idx = collection_step[ "id" ]
        return collect_step_idx

    def _extract_and_download_workflow( self, **extract_payload ):
        if "from_history_id" not in extract_payload:
            extract_payload[ "from_history_id" ] = self.history_id

        if "workflow_name" not in extract_payload:
            extract_payload[ "workflow_name" ] = "test import from history"

        for key in "job_ids", "dataset_ids", "dataset_collection_ids":
            if key in extract_payload:
                value = extract_payload[ key ]
                if isinstance(value, list):
                    extract_payload[ key ] = dumps( value )

        create_workflow_response = self._post( "workflows", data=extract_payload )
        self._assert_status_code_is( create_workflow_response, 200 )

        new_workflow_id = create_workflow_response.json()[ "id" ]
        download_response = self._get( "workflows/%s/download" % new_workflow_id )
        self._assert_status_code_is( download_response, 200 )
        downloaded_workflow = download_response.json()
        return downloaded_workflow

    def _get_steps_of_type( self, downloaded_workflow, type, expected_len=None ):
        steps = [ s for s in downloaded_workflow[ "steps" ].values() if s[ "type" ] == type ]
        if expected_len is not None:
            n = len( steps )
            assert n == expected_len, "Expected %d steps of type %s, found %d" % ( expected_len, type, n )
        return sorted( steps, key=operator.itemgetter("id") )

    def __job_id( self, history_id, dataset_id ):
        url = "histories/%s/contents/%s/provenance" % ( history_id, dataset_id )
        prov_response = self._get( url, data=dict( follow=False ) )
        self._assert_status_code_is( prov_response, 200 )
        return prov_response.json()[ "job_id" ]

    def __cat_job_id( self, history_id ):
        data = dict( history_id=history_id, tool_id="cat1" )
        jobs_response = self._get( "jobs", data=data )
        self._assert_status_code_is( jobs_response, 200 )
        cat1_job_id = jobs_response.json()[ 0 ][ "id" ]
        return cat1_job_id

    def _run_tool_get_collection_and_job_id( self, history_id, tool_id, inputs ):
        run_output1 = self.dataset_populator.run_tool(
            tool_id=tool_id,
            inputs=inputs,
            history_id=history_id,
        )
        implicit_hdca = run_output1[ "implicit_collections" ][ 0 ]
        job_id = run_output1[ "jobs" ][ 0 ][ "id" ]
        self.dataset_populator.wait_for_history( history_id, assert_ok=True, timeout=20 )
        return implicit_hdca, job_id

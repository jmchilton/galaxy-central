from base import api


HIDDEN_DURING_UPLOAD_DATATYPE = "fli"


class DatatypesApiTestCase( api.ApiTestCase ):

    def test_index( self ):
        datatypes = self._index_datatypes()
        for common_type in ["tabular", "fasta"]:
            assert common_type in datatypes, "%s not in %s" % (common_type, datatypes)

    def test_index_upload_only( self ):
        # fli is not displayed in upload - so only show it if upload_only
        # is explicitly false.
        datatypes = self._index_datatypes( data={ "upload_only": False } )
        assert HIDDEN_DURING_UPLOAD_DATATYPE in datatypes

        datatypes = self._index_datatypes( data={ "upload_only": True } )
        assert HIDDEN_DURING_UPLOAD_DATATYPE not in datatypes

        datatypes = self._index_datatypes( )
        assert HIDDEN_DURING_UPLOAD_DATATYPE not in datatypes

    def test_full_index( self ):
        datatypes = self._index_datatypes( data={ "extension_only": False } )
        for datatype in datatypes:
            self._assert_has_keys( datatype, "extension", "description", "description_url" )
            assert datatype["extension"] != HIDDEN_DURING_UPLOAD_DATATYPE

    def test_mapping( self ):
        response = self._get( "datatypes/mapping" )
        self._assert_status_code_is( response, 200 )
        mapping_dict = response.json()
        self._assert_has_keys( mapping_dict, "ext_to_class_name", "class_to_classes" )

    def test_sniffers( self ):
        response = self._get( "datatypes/sniffers" )
        self._assert_status_code_is( response, 200 )
        sniffer_list = response.json()
        owl_index = sniffer_list.index( "galaxy.datatypes.xml:Owl" )
        xml_index = sniffer_list.index( "galaxy.datatypes.xml:GenericXml" )
        assert owl_index < xml_index

    def _index_datatypes( self, data={} ):
        response = self._get( "datatypes", data=data )
        self._assert_status_code_is( response, 200 )
        datatypes = response.json()
        assert isinstance( datatypes, list )
        return datatypes

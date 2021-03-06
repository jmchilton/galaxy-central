import os, shutil, urllib, StringIO
from galaxy import datatypes, jobs
from galaxy.datatypes import sniff

class UploadToolAction( object ):
    """
    Action for uploading files
    """
    def execute( self, tool, trans, incoming={} ):
        
        data_file = incoming['file_data']
        file_type = incoming['file_type']
        dbkey = incoming['dbkey']
        url_paste = incoming['url_paste']
        info = "uploaded file"
        temp_name = ""
        data_list = []
        if 'filename' in dir(data_file):
            try:
                file_name = data_file.filename
                file_name = file_name.split('\\')[-1]
                file_name = file_name.split('/')[-1]
                data_list.append( self.add_file(trans, data_file.file, file_name, file_type, dbkey, "uploaded file") )
            except:
                pass
        
        if url_paste not in [None, ""]:
            if url_paste[0:7].lower() == "http://" or url_paste[0:6].lower() == "ftp://" :
                url_paste = url_paste.replace("\r","").split("\n")
                for line in url_paste:
                    try:
                        data_list.append( self.add_file(trans, urllib.urlopen(line), line, file_type, dbkey, "uploaded url") )
                    except:
                        pass
            else:
                try:
                    data_list.append( self.add_file(trans, StringIO.StringIO(url_paste), 'Pasted Entry', file_type, dbkey, "pasted entry") )
                except:
                    pass
        
        if len(data_list)<1:
            return self.upload_failed(trans, "ERROR: No file specified or Invalid URL","upload failed, the url specified is invalid or you have not specified a file")
        return dict( output=data_list[0] )

    def upload_failed(self, trans, err_code, err_msg):
        data = trans.app.model.Dataset()
        data.name = err_code 
        data.extension = "text"
        data.dbkey = "?"
        data.info = err_msg
        data.flush()
        data.state = jobs.JOB_ERROR
        trans.history.add_dataset( data )
        trans.app.model.flush()
        return dict( output=data )

    def add_file(self, trans, file_obj, file_name, file_type, dbkey, info ):
        temp_name = sniff.stream_to_file(file_obj)
        sniff.convert_newlines(temp_name)
        if file_type == 'auto':
            ext = sniff.guess_ext(temp_name)    
        else:
            ext = file_type

        data = trans.app.model.Dataset()
        data.name = file_name
        data.extension = ext
        data.dbkey = dbkey
        data.info = info
        data.flush()
        shutil.move(temp_name, data.file_name)
        data.state = data.states.OK
        data.init_meta()
        data.set_peek()
        if isinstance( data.datatype, datatypes.interval.Interval ):
            if data.missing_meta():
                data.extension = 'tabular'
        trans.history.add_dataset( data )
        trans.app.model.flush()
        return data

// dependencies
define(['utils/utils'], function(Utils) {

// widget
return Backbone.Collection.extend(
{
    // list of datasets
    list: {},
    
    // cache for datablocks
    cache: {},
    
    // initialize
    initialize: function(app, options)
    {
        // link app
        this.app = app;
        
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
    },
    
    // wait
    request: function(request_dictionary, success, error) {
        // link this
        var self = this;
        
        // check if column data is requested
        if (request_dictionary.groups) {
            this._get_dataset(request_dictionary.id, function() {
                self._get(request_dictionary, success);
            });
        } else {
            this._get_dataset(request_dictionary.id, success, error)
        }
    },
    
    // get dataset
    _get_dataset: function(id, success, error) {
        // check if dataset is available from cache
        var dataset = this.list[id];
        if (dataset) {
            success(dataset);
            return;
        }
    
        // request dataset
        var self = this;
        Utils.request('GET', config.root + 'api/datasets/' + id, {}, function(dataset) {
            switch (dataset.state) {
                case 'error':
                    if (error) {
                        error(dataset);
                    }
                    break;
                default:
                    self.list[id] = dataset;
                    success(dataset);
            }
        });
    },
    
    // get block id
    _block_id: function (options, column) {
        return options.id + '_' + options.start + '_' + options.end + '_' + column;
    },
    
    // fills request dictionary with data from cache/response
    _get: function(request_dictionary, callback) {
        // set start/end
        if (!request_dictionary.start) {
            request_dictionary.start = 0;
        }
        if (!request_dictionary.end) {
            request_dictionary.end = this.app.config.get('query_limit');
        }
        // get column indices
        var column_list = [];
        var column_map  = {};
        var column_count = 0;
        for (var i in request_dictionary.groups) {
            var group = request_dictionary.groups[i];
            for (var key in group.columns) {
                // identify column
                var column = group.columns[key].index;
                
                // check if column is in cache
                var block_id = this._block_id(request_dictionary, column);
                if (this.cache[block_id] || column === 'auto') {
                    continue;
                }
                
                // add to dictionary
                if (!column_map[column] && column !== undefined) {
                    column_map[column] = column_count;
                    column_list.push(column);
                    column_count++;
                }
            }
        }
        
        // check length
        if (column_list.length == 0) {
            // fill dictionary from cache
            this._fill_from_cache(request_dictionary);
            
            // parse requested data
            callback(request_dictionary);
            
            // return
            return;
        }
        
        // configure dataset request dictionary
        var dataset_request = {
            dataset_id  : request_dictionary.id,
            start       : request_dictionary.start,
            end         : request_dictionary.end,
            columns     : column_list
        }
        
        // fetch data
        var self = this;
        this._fetch(dataset_request, function(results) {
            // add results to cache
            for (var i in results) {
                var column = column_list[i];
                var block_id = self._block_id(request_dictionary, column);
                self.cache[block_id] = results[i];
            }
            
            // fill dictionary from cache
            self._fill_from_cache(request_dictionary);
            
            // trigger callback
            callback(request_dictionary);
        });
    },
    
    // convert
    _fill_from_cache: function(request_dictionary) {
        // log
        console.debug('Datasets::_fill_from_cache() - Filling request from cache.');
    
        // get dataset
        var dataset = this.list[request_dictionary.id];
        if (!dataset) {
            console.debug('FAILED - Datasets::_fill_from_cache() - Dataset not found.');
        }
        
        // identify start/end of request
        var start = request_dictionary.start;
        var end   = Math.min(request_dictionary.end, dataset.metadata_data_lines);
        if (end - start <= 0) {
            console.debug('FAILED - Datasets::_fill_from_cache() - Invalid range.');
        }
        
        // initialize group values
        for (var i in request_dictionary.groups) {
            // get group
            var group = request_dictionary.groups[i];
            
            // reset group
            group.values = [];
        
            // add values
            for (var j = 0; j < end - start; j++) {
                // add default x values
                group.values[j] = {
                    x : parseInt(j) + start
                };
            }
        }
        
        // collect all data into the defined groups
        for (var i in request_dictionary.groups) {
            // get group
            var group = request_dictionary.groups[i];
            
            // fill value
            for (var key in group.columns) {
                // get column
                var column = group.columns[key];
          
                // check if auto block is requested
                if (column.index == 'auto') {
                    for (var j = start; j < end; j++) {
                        // get value dictionary
                        var value = group.values[j];
                        
                        // add auto value
                        value[key] = parseInt(j) + start;
                    }
                } else {
                    // get block
                    var block_id = this._block_id(request_dictionary, column.index);
                    var column_data = this.cache[block_id];
                
                    // go through column
                    for (var j = start; j < end; j++) {
                        // get value dictionary
                        var value = group.values[j];
                        
                        // get/fix value
                        var v = column_data[j];
                        if (isNaN(v) && !column.is_label) {
                            v = 0;
                        }
                        
                        // add to dict
                        value[key] = v;
                    }
                }
            }
        }
    },
    
    // fetch data columns into dataset object
    _fetch: function(dataset_request, callback) {
        // set offset
        var offset  = dataset_request.start ? dataset_request.start : 0;
        
        // set limit
        var limit   = Math.abs(dataset_request.end - dataset_request.start);
        var query_limit = this.app.config.get('query_limit');
        if (!limit || limit > query_limit) {
            limit = query_limit;
        }
        
        // check length
        var n_columns = 0;
        if (dataset_request.columns) {
            n_columns = dataset_request.columns.length;
            console.debug('Datasets::_fetch() - Fetching ' + n_columns + ' column(s)');
        }
        if (n_columns == 0) {
            console.debug('Datasets::_fetch() - No columns requested');
        }
        
        // get column indices
        var column_string    = '';
        for (var i in dataset_request.columns) {
            column_string += dataset_request.columns[i] + ',';
        }
        column_string = column_string.substring(0, column_string.length - 1);
        
        // make request
        var self = this;
        Utils.request('GET', config.root + 'api/datasets/' + dataset_request.dataset_id, {
                data_type   : 'raw_data',
                provider    : 'dataset-column',
                limit       : limit,
                offset      : offset,
                indeces     : column_string
            }, function(response) {
                // initialize result dictionary
                var result = new Array(n_columns);
                for (var i = 0; i < n_columns; i++) {
                    result[i] = [];
                }
                
                // loop through rows
                for (var i in response.data) {
                    // get row
                    var row = response.data[i];
                    
                    // collect all data into the defined groups
                    for (var j in row) {
                        // get group
                        var v = row[j];
                        if (v !== undefined && v != 2147483647) {
                            // add to result
                            result[j].push(v);
                        }
                    }
                }
                
                // log
                console.debug('Datasets::_fetch() - Fetching complete.');
        
                // callback
                callback(result);
            }
        );
    }
});

});
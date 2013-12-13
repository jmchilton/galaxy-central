// =================================================================== BOILER PLATE
try {
    var utils = require( 'utils' ),
        xpath = require( 'casper' ).selectXPath,
        format = utils.format,

        //...if there's a better way - please let me know, universe
        scriptDir = require( 'system' ).args[3]
            // remove the script filename
            .replace( /[\w|\.|\-|_]*$/, '' )
            // if given rel. path, prepend the curr dir
            .replace( /^(?!\/)/, './' ),
        spaceghost = require( scriptDir + 'spaceghost' ).create({
            // script options here (can be overridden by CLI)
            //verbose: true,
            //logLevel: debug,
            scriptDir: scriptDir
        });

    spaceghost.start();

} catch( error ){
    console.debug( error );
    phantom.exit( 1 );
}


spaceghost.loginTestUser();

spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){
    this.test.comment( 'Creating history with two datasets to test.' );

    var newHistoryName = 'Collection History';
    var createdHistory = this.api.histories.create({ name: newHistoryName });
    var historyId      = createdHistory["id"];
    var testDatasets   = this.createTestDatasets( historyId, 2 );
    
});


// ===================================================================
spaceghost.run( function(){
});

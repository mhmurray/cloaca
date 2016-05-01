require.config({
    paths: {
//        jquery: 'libs/jquery/jquery',
//        jquery-ui: 'libs/jquery/jquery-ui',
        jquery: "https://ajax.googleapis.com/ajax/libs/jquery/1.12.0/jquery.min",
        jqueryui: "https://ajax.googleapis.com/ajax/libs/jqueryui/1.11.4/jquery-ui.min",
        sockjs: "https://cdnjs.cloudflare.com/ajax/libs/sockjs-client/1.0.3/sockjs",
        fsm: "libs/javascript-state-machine/state-machine.min"
    },
    
    // Stop caching files served with require
    urlArgs: "bust=" +  (new Date()).getTime()
});

require(['app'], function(App){
    App.initialize();
});

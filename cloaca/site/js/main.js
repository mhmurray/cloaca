require.config({
    paths: {
//        jquery: 'libs/jquery/jquery',
        jquery: "https://ajax.googleapis.com/ajax/libs/jquery/1.12.0/jquery.min",
        fsm: "libs/javascript-state-machine/state-machine.min"
    },
});

require(['app'], function(App){
    App.initialize();
});

require.config({
    paths: {
        //jquery: 'libs/jquery/jquery',
        jquery: "https://cdnjs.cloudflare.com/ajax/libs/jquery/3.1.1/jquery.min",
        //waypoints: 'libs/jquery/noframework.waypoints.min',
        waypoints: 'https://cdnjs.cloudflare.com/ajax/libs/waypoints/4.0.1/noframework.waypoints.min',
        fsm: "libs/javascript-state-machine/state-machine.min"
    },
});

require(['app'], function(App){
    App.initialize();
});

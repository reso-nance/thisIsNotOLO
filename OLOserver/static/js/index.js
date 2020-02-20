$( document ).ready(function() {
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + '/home')  
    var isRecording = false;
    var timeStarted = 0;
    var recordedSequence = [];

    $(document).on('click', '#rec', function(event){
        if (isRecording) {
            $("#rec").removeClass("btn-warning").addClass("btn-danger");
            isRecording = false;
            console.log( "finished recording :", recordedSequence);
        }
        else {
            $("#rec").removeClass("btn-danger").addClass("btn-warning");
            isRecording = true;
            timeStarted = Date.now();
            console.log( "recording...");
        }   
        // socket.emit("dispatchFileToClients", {"filename":filename, "clientList":clientList});
     });

    $(document).on('mousedown', '.window', function(event){
        console.log("windows clicked : ", $(event.target));
        recordedSequence.push([Date.now()-timeStarted, 1, 100]);
    });

    $(document).on('mouseup', '.window', function(event){
        console.log("windows released: ", $(event.target));
        recordedSequence.push([Date.now()-timeStarted, 1, 0]);
    });

    // // update connected devices on server request
    // socket.on('deviceList', function(data) {
    //     connectedDevices = Object.values(data);
    //     updateDeviceList();
    // });
    
});
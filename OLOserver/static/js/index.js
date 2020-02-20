window.oncontextmenu = function(event) {
    event.preventDefault();
    event.stopPropagation();
    return false;
};

$( document ).ready(function() {
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + '/home')  
    var isRecording = false;
    var timeStarted = 0;
    var recordedSequence = [];
    $("#play").hide();
    var sequenceID = 0; 

    $(document).on('click', '#rec', function(event){
        if (isRecording) {
            $("#rec").removeClass("btn-warning").addClass("btn-danger");
            isRecording = false;
            endSequence();
            console.log( "finished recording :", recordedSequence);
            $("#rec").text("startRec");
            $("#play").show();
        }
        else {
            $("#rec").removeClass("btn-danger").addClass("btn-warning");
            isRecording = true;
            timeStarted = Date.now();
            recordedSequence=[];
            sequenceID = Math.floor((Math.random() * 10000000000000000) + 1);
            console.log( "recording...");
            $("#rec").text("stopRec");
            $("#play").hide();
        }   
        // socket.emit("dispatchFileToClients", {"filename":filename, "clientList":clientList});
     });

     $(document).on("click", "#play", function(event) {
         if (recordedSequence.length > 0 && !isRecording) {
             console.log("sending sequence to server");
             socket.emit("newSequence", sequenceID, recordedSequence);
         }
     });

     $(document).on("click", "#remove", function(event) {
         if (recordedSequence.length > 0 && !isRecording) {
             console.log("removing this sequence");
             socket.emit("removeSequence", sequenceID);
         }
     });

     $(document).on("click", "#clear", function(event) {
            socket.emit("clearAllSequences");
     });

    $(document).on('mousedown', '.window', function(event){
        const windowID = $(event.target).attr("data-id");
        console.log("windows clicked : ", windowID);
        recordedSequence.push([Date.now()-timeStarted, windowID, 100]);
    });

    $(document).on('mouseup', '.window', function(event){
        const windowID = $(event.target).attr("data-id");
        console.log("windows released : ", windowID);
        recordedSequence.push([Date.now()-timeStarted, windowID, 0]);
    });

    // add an off element at the end of the sequence to reserve space for the loop
    function endSequence() {
        const lastWindowUsed = recordedSequence[recordedSequence.length-1][2];
        recordedSequence.push([Date.now()-timeStarted, lastWindowUsed, 0]);
    }

    // // update connected devices on server request
    // socket.on('deviceList', function(data) {
    //     connectedDevices = Object.values(data);
    //     updateDeviceList();
    // });
    
});
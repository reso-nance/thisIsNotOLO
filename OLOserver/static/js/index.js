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
    const notes=["C3", "E3", "G3", "G4", "E4", "G4", "C5", "E5"];

    var synth = new Tone.PolySynth(3, Tone.Synth, {
        "oscillator" : {
            "type" : "fatsine",
            "count" : 3,
            "spread" : 30
        },
        "envelope" : {
            "attack" : 0.1,
            "decay" : 0.1,
            "sustain" : 0.5,
            "release" : 0.4,
            "attackCurve" : "exponential"
        },
    }).toMaster();
    var reverb = new Tone.Reverb().toMaster();

    $(document).on('click', '#rec', function(event){
        if (isRecording) {
            $("#rec").removeClass("btn-warning").addClass("btn-danger");
            isRecording = false;
            if (recordedSequence.length>2){
                endSequence();
                console.log( "finished recording :", recordedSequence);
                $("#play").show();
            }
            else console.log("finished empty recording");
            $("#rec").text("startRec");
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

    $(document).on('touchstart', '.window', function(event){
        event.preventDefault(); // prevent the opening of a context menu on long press
        $(event.target).css("background-color", "lightgray");
        lightEvent($(event.target).attr("data-id"), 100);
    });

    $(document).on('touchend', '.window', function(event){
        event.preventDefault(); // prevent the opening of a context menu on long press
        $(event.target).css("background-color", "darkslategray");
        lightEvent($(event.target).attr("data-id"), 0);
    });

    $(document).on('mousedown', '.window', function(event){
        $(event.target).css("background-color", "lightgray");
        lightEvent($(event.target).attr("data-id"), 100);
    });

    $(document).on('mouseup', '.window', function(event){
        $(event.target).css("background-color", "darkslategray")
        lightEvent($(event.target).attr("data-id"), 0);
    });

    function lightEvent(lampID, value){
        recordedSequence.push([Date.now()-timeStarted, lampID, value]);
        const action = (value == 0) ? "released" : "clicked"
        const note = notes[parseInt(lampID)];
        if ( value == 0) synth.triggerRelease(note, undefined);
        else synth.triggerAttack(note, undefined); // note or array, time, velocity 0~1
        // const audioElement = document.getElementById("audio"+lampID); 
        // if (value == 0) audioElement.pause();
        // else {
        //     audioElement.play();
        //     audioElement.currentTime = 0;
        // }
        console.log("window", lampID, action);
    }
    // add a 0 element at the end of the sequence to reserve space at the end of the loop
    function endSequence() {
        if (recordedSequence.length<2) return;
        const lastWindowUsed = recordedSequence[recordedSequence.length-1][2];
        recordedSequence.push([Date.now()-timeStarted, lastWindowUsed, 0]);
    }

    // https://stackoverflow.com/questions/7942452/javascript-slowly-decrease-volume-of-audio-element/7942472#7942472
    // function fadeVolume(volume, callback)
    //     var factor  = 0.01,
    //         speed   = 50;
    //     if (volume > factor){
    //         setTimeout(function(){
    //             fadeVolume((audio.volume -= factor), callback);         
    //         }, speed);
    //     }
    //     else (typeof(callback) !== 'function') || callback();
    //     fadeVolume(audio.volume, function(){
    //     console.log('fade complete');
    // });

    // // update connected devices on server request
    // socket.on('deviceList', function(data) {
    //     connectedDevices = Object.values(data);
    //     updateDeviceList();
    // });
    
});
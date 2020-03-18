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
    console.log("notes", $("#notes").text())
    const notes =  ($("#notes").text()).split(",");// will be generated on the backend depending on the lightCount
    const activeWindows = ($("#activeWindows").text()).split(","); // get active window from the backend
    const maxSequenceLength = parseInt($("#seqMaxLength").text());
    console.log($("#seqMaxLength"))
    // const maxSequenceLength = 30000; //  in millis, recording will stop when this time has been reached
    // for example : ["C3", "E3", "G3", "G4", "E4", "G4", "C5", "E5"];
    console.log("active windows :", activeWindows);
    displayWindows();

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
            clearInterval(); // stop checkMaxSequenceLength
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
            window.setInterval(function(){checkMaxSequenceLength()}, 1000); // check every sec that we are not exceeding max sequence duration
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

    $(document).on('touchstart', '.window-active', function(event){
        event.preventDefault(); // prevent the opening of a context menu on long press
        $(event.target).css("background-color", "lightgray");
        lightEvent($(event.target).attr("data-id"), 100);
    });

    $(document).on('touchend', '.window-active', function(event){
        event.preventDefault(); // prevent the opening of a context menu on long press
        $(event.target).css("background-color", "darkslategray");
        lightEvent($(event.target).attr("data-id"), 0);
    });

    $(document).on('mousedown', '.window-active', function(event){
        $(event.target).css("background-color", "lightgray");
        lightEvent($(event.target).attr("data-id"), 100);
    });

    $(document).on('mouseup', '.window-active', function(event){
        $(event.target).css("background-color", "darkslategray")
        lightEvent($(event.target).attr("data-id"), 0);
    });

    socket.on('playNoteForWindow', function(data) {
        playNote(String(data.windowID), data.value);
    });

    function lightEvent(lampID, value){
        recordedSequence.push([Date.now()-timeStarted, lampID, value]);
        playNote(lampID, value);
        console.log("window", lampID, (value == 0) ? "released" : "clicked");
    }

    function playNote(lampID, value){
        const noteIndex = activeWindows.indexOf(lampID);
        const note = notes[noteIndex];
        if (value == 0) synth.triggerRelease(note, undefined);
        else synth.triggerAttack(note, undefined, value/100); // note or array, time, velocity 0~1
        // else synth.triggerAttack(note, undefined, value/100); // note or array, time, velocity 0~1
        // const audioElement = document.getElementById("audio"+lampID); 
        // if (value == 0) audioElement.pause();
        // else {
        //     audioElement.play();
        //     audioElement.currentTime = 0;
        // }
    }

    // add a 0 element at the end of the sequence to reserve space at the end of the loop
    function endSequence() {
        if (recordedSequence.length<2) return;
        const lastWindowUsed = recordedSequence[recordedSequence.length-1][2];
        recordedSequence.push([Date.now()-timeStarted, lastWindowUsed, 0]);
    }

    // check that the sequence doesn't exceed maxSequenceLength
    function checkMaxSequenceLength() {
        if (isRecording && Date.now()-timeStarted > maxSequenceLength) {
            $("#rec").trigger("click");
            console.log("reached max sequence duration of", maxSequenceLength, "ms : current duration :", Date.now()-timeStarted);
        }
    }

    // add the class window-active or window-inactive depending on the windows ID being in the activeWindows array
    function displayWindows() {
        for (let i=0; i < 12; i++) {
            i = String(i);
            let window = $(".window[data-id='"+i+"']");
            if (activeWindows.includes(i)) window.addClass("window-active");
            else window.addClass("window-inactive");
        }
    }
    
});
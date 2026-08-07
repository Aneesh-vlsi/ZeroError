# voice_engine.py

tts_javascript = """
(voice_persona, text_to_speak, current_code_panel_value) => {
    // 1. Instantly flush out stuck queues to ensure zero audio overlap
    window.speechSynthesis.cancel();
    window.arroSpeechCancelFlag = false; // Reset the halt flag on a fresh play request
    
    // Wake up audio context layers for mobile browsers (WebKit / iOS limitations)
    let audioContextWakeup = new SpeechSynthesisUtterance("");
    window.speechSynthesis.speak(audioContextWakeup);
    
    // 2. Strict UI Guard validation: intercept empty or failed generations instantly
    if (!current_code_panel_value || current_code_panel_value.trim() === "" || 
        current_code_panel_value.includes("INVALID") || current_code_panel_value.includes("MISSING") || 
        current_code_panel_value.includes("ERROR")) {
        
        let alertMessage = "Attention. Please enter your project parameters and run compilation successfully before requesting an AI voice assistant walkthrough.";
        let u = new SpeechSynthesisUtterance(alertMessage);
        u.lang = "en-US";
        u.rate = 0.95; 
        window.speechSynthesis.speak(u);
        return;
    }

    if (!text_to_speak || text_to_speak.trim() === "") return;

    // 3. Premium Phonetic Smoothing & Expanded Technical Translations
    let sanitizedText = text_to_speak
        .replace(/✔/g, " verified ")
        .replace(/❌/g, " failed ")
        .replace(/⚠️/g, " warning ")
        .replace(/STM32/gi, " S-T-M 32 ")
        .replace(/ESP32/gi, " E-S-P 32 ")
        .replace(/ESP8266/gi, " E-S-P 82 66 ")
        .replace(/GPIO/gi, " G-P-I-O ")
        .replace(/MCU/gi, " microcontroller ")
        .replace(/OLED/gi, " O-L-E-D screen ")
        .replace(/LCD/gi, " L-C-D display ")
        .replace(/I2C/gi, " I-2-C ")
        .replace(/SPI/gi, " S-P-I ")
        .replace(/PWM/gi, " P-W-M ")
        .replace(/PIN/gi, " pin ")
        .replace(/LED/gi, " L-E-D ")
        .replace(/I'll/gi, " I will ")
        .replace(/let's/gi, " let us ")
        .replace(/[#*\\[\\]{}()\\-+_=\\/\\\\|:;<>\'"`]/g, " ")

        .trim();

    // Split text cleanly by punctuation to manage steady breath gaps
    let cleanSentences = sanitizedText.split(/[.!?;]+/)
        .map(s => s.trim())
        .filter(s => s.length > 2);

    if (cleanSentences.length === 0) return;

    let targetIndex = 0;

    // 4. Ultra-Smooth Sequential Playback Queue Manager
    function executeSpeechQueue() {
        // CRITICAL GUARD: Stop processing if the cancel flag has been raised by the user
        if (window.arroSpeechCancelFlag === true || targetIndex >= cleanSentences.length) return;

        let utterance = new SpeechSynthesisUtterance(cleanSentences[targetIndex] + ".");
        
        let voicesList = window.speechSynthesis.getVoices();
        let chosenVoice = null;

        utterance.rate = 0.92; 
        utterance.pitch = 1.0;
        
        let personaLabel = String(voice_persona).toLowerCase();

        if (personaLabel.includes("may")) {
            utterance.lang = "en-US";
            chosenVoice = voicesList.find(v => v.lang.startsWith("en-US") && (v.name.includes("Natural") || v.name.includes("Premium") || v.name.includes("Samantha") || v.name.includes("Zira")));
            utterance.pitch = 1.02;
        } 
        else if (personaLabel.includes("heera")) {
            utterance.lang = "en-IN";
            chosenVoice = voicesList.find(v => v.lang.replace("_", "-").includes("en-IN") && (v.name.includes("Natural") || v.name.includes("Premium") || v.name.includes("Google") || v.name.includes("Heera") || v.name.includes("Rishi")));
        } 
        else if (personaLabel.includes("max")) {
            utterance.lang = "en-US";
            chosenVoice = voicesList.find(v => v.lang.startsWith("en-US") && (v.name.includes("Natural") || v.name.includes("David") || v.name.includes("Male") || v.name.includes("Google")));
            utterance.pitch = 0.94;
        } 
        else if (personaLabel.includes("jimmy")) {
            utterance.lang = "en-GB";
            chosenVoice = voicesList.find(v => v.lang.startsWith("en-GB") && (v.name.includes("Natural") || v.name.includes("Premium") || v.name.includes("Hazel") || v.name.includes("Google")));
            utterance.rate = 1.05; 
        }

        if (!chosenVoice) { chosenVoice = voicesList.find(v => v.lang.replace("_", "-").startsWith(utterance.lang)); }
        if (!chosenVoice) { chosenVoice = voicesList.find(v => v.lang.startsWith("en")); }

        if (chosenVoice) utterance.voice = chosenVoice;

        utterance.onend = function() {
            // Only queue up the next sentence if the user hasn't pressed stop
            if (window.arroSpeechCancelFlag !== true) {
                setTimeout(() => {
                    targetIndex++;
                    executeSpeechQueue();
                }, 120);
            }
        };

        utterance.onerror = function() {
            if (window.arroSpeechCancelFlag !== true) {
                targetIndex++;
                executeSpeechQueue();
            }
        };

        window.speechSynthesis.speak(utterance);
    }

    // Fire the stable engine queue
    executeSpeechQueue();
}
"""

# FIXED: Explicitly raises the cancel flag to clear and block the background execution loop immediately
stop_tts_javascript = """
() => {
    window.arroSpeechCancelFlag = true;
    window.speechSynthesis.cancel();
}
"""

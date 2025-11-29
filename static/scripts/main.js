// --- Helper Function to Update Agent Visuals (for feedback) ---
function updateAgentState(state) {
    const chatInterface = document.getElementById('chat-interface');
    
    // Simple state indicators for visual feedback
    if (state === 'excited') {
        chatInterface.style.borderColor = '#ff4081'; // Pink for success
    } else if (state === 'confused') {
        chatInterface.style.borderColor = '#ff9800'; // Orange for confusion/error
    } else {
        chatInterface.style.borderColor = '#ccc'; // Grey for neutral/thinking
    }
}

// --- NEW: Audio Playback Function ---
let isPlaying = false;
function playPoem() {
    const audio = document.getElementById('poem-audio');
    const button = document.getElementById('play-poem-button');

    if (isPlaying) {
        audio.pause();
        audio.currentTime = 0; // Rewind
        button.innerHTML = '🎶 Hear Harsh\'s Voice!';
        isPlaying = false;
    } else {
        // Stop any currently playing audio and play the new one
        audio.play();
        button.innerHTML = '⏸ Stop the Music';
        isPlaying = true;
        // Reset state when audio ends
        audio.onended = () => {
            button.innerHTML = '🎶 Hear Harsh\'s Voice!';
            isPlaying = false;
        };
    }
}


// Function to switch from the welcome page to the gift hunt page
function goToGiftSection() {
    document.getElementById('welcome-container').style.display = 'none';
    const giftSection = document.getElementById('gift-hunt-section');
    // We use display:flex as defined in the CSS for the chat layout
    giftSection.style.display = 'flex'; 
    
    // Send the first message to the backend to start the game
    sendMessage("START_GAME_INIT", true);
}

// Function to add messages to the chat history
function addMessage(text, sender) {
    const history = document.getElementById('chat-history');
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message');
    msgDiv.classList.add(sender === 'agent' ? 'agent-message' : 'user-message');
    
    // Use innerHTML to render HTML content (like line breaks and bolding)
    msgDiv.innerHTML = `<p>${text}</p>`;
    history.appendChild(msgDiv);
    
    // Auto-scroll to the latest message
    history.scrollTop = history.scrollHeight;
}

// --- CORE CHAT LOGIC ---
async function sendMessage(initialMessage = null, isSystem = false) {
    const inputField = document.getElementById('user-input');
    let userMessage = initialMessage || inputField.value.trim();

    if (!userMessage && !isSystem) return;

    if (!isSystem) {
        addMessage(userMessage, 'user');
        inputField.value = ''; // Clear input field
    }
    
    addMessage("Agent is thinking...", 'agent');
    const loadingMessage = document.getElementById('chat-history').lastChild;

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ message: userMessage })
        });

        const data = await response.json();
        
        loadingMessage.remove(); 

        let agentResponseText = data.response_text;
        
        // --- NEW: Audio Button Enablement and State Check ---
        // The SUCCESS_UNLOCK status means the first poem has been delivered.
        if (agentResponseText.includes("YES! You got it right!")) {
             document.getElementById('play-poem-button').disabled = false;
        }
        
        // Disable audio button again when she hits "I'm done" and moves to the next gift/lock
        if (agentResponseText.includes("HUH! You're a little too fast") || agentResponseText.includes("Your next challenge is:")) {
             document.getElementById('play-poem-button').disabled = true;
             // Ensure audio stops if playing
             document.getElementById('poem-audio').pause();
             document.getElementById('play-poem-button').innerHTML = '🎶 Hear Harsh\'s Voice!';
             isPlaying = false;
        }
        // ---------------------------------------------

        // Replace newlines with <br> for HTML rendering
        agentResponseText = agentResponseText.replace(/\n/g, '<br>');

        addMessage(agentResponseText, 'agent');
        updateAgentState(data.agent_state);
        
    } catch (error) {
        loadingMessage.remove();
        console.error("Error communicating with AI backend:", error);
        addMessage("Agent Cupid is experiencing technical turbulence! Please try your message again.", 'agent');
        updateAgentState('confused');
    }
}

// ----------------------------------------------------
// Attach the function to the buttons and input fields *after* the page and script have fully loaded
document.addEventListener('DOMContentLoaded', () => {
    const startButton = document.getElementById('gift-section-button');
    const sendButton = document.getElementById('send-button');
    const inputField = document.getElementById('user-input');
    
    // Link button click to function
    if (startButton) {
        startButton.addEventListener('click', goToGiftSection);
    }
    
    // Link send button click to function
    if (sendButton) {
        sendButton.addEventListener('click', () => sendMessage());
    }
    
    // Link Enter key press to send message
    if (inputField) {
        inputField.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                sendMessage();
            }
        });
    }

    // Initialize the small agent model to auto-rotate in the chat view
    const chatModel = document.getElementById('chat-agent-model');
    if(chatModel) {
        chatModel.setAttribute('auto-rotate', '');
    }
});
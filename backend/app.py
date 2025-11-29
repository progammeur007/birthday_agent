import os
from flask import Flask, request, jsonify, render_template
from google import genai
from google.genai import types 
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Import tools, state, and generators
from agent_tools import GIFT_STATUS, generate_next_agent_prompt
from gemini_generator import generate_text_content, generate_image_content

# --- CONFIGURATION FOR ABSOLUTE PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'static') 

# --- FIX: Explicitly Load .env file from the backend/ directory ---
DOTENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(DOTENV_PATH) 

# --- FLASK APP SETUP ---
app = Flask(__name__, 
            static_folder=FRONTEND_DIR,          
            template_folder=FRONTEND_DIR,        
            static_url_path='')                  

# --- GEMINI CLIENT & CONFIG SETUP ---
try:
    client = genai.Client()
    SYSTEM_INSTRUCTION = (
        "You are **Agent Cupid**, a highly personalized, witty, and charming AI assistant created by Harsh specifically for Anushka's birthday hunt. "
        "Your tone is modern, supportive, enthusiastic, and highly familiar with Anushka and Harsh's relationship (you know their inside jokes). "
        "**CRITICAL PERSONA RULE:** NEVER use overly formal or generic romantic filler. Use familiar, genuine language. "
        "Your responses must be short, cheerful, and focused on the game's progress. "
        "You manage a linear game state. "
        "RULES:\n"
        "1. **Check Status:** You MUST always receive a status report from the Game Master. Pay attention to the STATUS. You should only speak if the status is FAILURE_CLUE, GUARDRAIL_VIOLATION, or UNKNOWN. Python handles all SUCCESS, LOCKED, and DELIVER status messages directly.\n"
        "2. **Guardrail:** If the status shows 'GUARDRAIL_VIOLATION', you MUST use the exact phrase: 'Uh oh! Harsh didn't allow me to do so for this request! We must focus on the task at hand.'\n"
    )
    
    AGENT_CONFIG = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.7,
        max_output_tokens=150
    )
    
    print("Gemini Client initialized successfully.")
    
except Exception as e:
    print(f"FATAL: Error initializing Gemini client. Check API Key or connectivity. Error: {e}")
    client = None

# --- WEB ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    if not client:
        return jsonify({"response_text": "AI service is unavailable. Please check the server logs for FATAL errors.", "agent_state": "confused"}), 500
    
    user_message = request.json.get('message', '')
    
    # 1. INITIALIZE AND START GAME
    if user_message == "START_GAME_INIT":
        first_clue = GIFT_STATUS["clues"][0]['clue_question']
        return jsonify({
            'response_text': f"Welcome to the hunt! I'm Agent Cupid, your guide. Your first gift, 'The Birthday Bard,' is locked. To unlock it, answer this: **{first_clue}**",
            'agent_state': 'excited'
        })
        
    # --- CORE AGENTIC LOOP ---

    # 2. Get game status and next command from the Python State Manager
    current_state_command = generate_next_agent_prompt(user_message)
    
    # 3. Handle successful CLUE UNLOCK (Python delivers the content)
    if current_state_command.startswith("STATUS: SUCCESS_UNLOCK."):
        
        initial_content_raw = current_state_command.split("INITIAL_CONTENT:")[1].split(". CUSTOMIZATION_PROMPT:")[0].strip()
        customization_prompt_raw = current_state_command.split("CUSTOMIZATION_PROMPT:")[1].strip()
        
        final_response = (
            f"**YES! You got it right!**<br>Agent Cupid is thrilled to unlock your first gift: **The Birthday Bard!**<br><br>"
            f"***{initial_content_raw.replace('\n', '<br>')}***<br><br>"
            f"<hr style='border-top: 1px solid #ff99aa; margin: 15px 0;'>**Next Step:** {customization_prompt_raw}"
        )
        return jsonify({'response_text': final_response, 'agent_state': 'excited'})
    
    # 4. Handle LLM call for customization
    if current_state_command.startswith("AGENT_COMMAND: GENERATE_TEXT"):
        try:
            prompt = current_state_command.split("PROMPT:")[1].strip()
            content = generate_text_content(client, prompt) 
            
            GIFT_STATUS["clues"][0]["current_poem"] = content
            
            final_response = (
                f"**REVISED DRAFT!**<br>Agent Cupid has refined the poem based on your notes:<br><br>"
                f"***{content.replace('\n', '<br>')}***<br><br>**How is that? Want another edit, or are you ready to say 'I'm done!'?**"
            )
            return jsonify({'response_text': final_response, 'agent_state': 'excited'})
        
        except Exception as e:
            return jsonify({'response_text': f"Agent Cupid failed to generate the gift content due to a system error. Error: {e}", 'agent_state': 'confused'})

    # 5. Handle Time Lock / Next Clue Delivery (Pure Python Logic)
    
    if current_state_command.startswith("STATUS: GIFT_LOCKED_BY_TIME."):
        # Extract time and name from the pure Python status
        parts = current_state_command.split('. ')
        time_data = next(p for p in parts if p.startswith("TIME_REMAINING:"))[len("TIME_REMAINING:"):].strip()
        gift_name = next(p for p in parts if p.startswith("GIFT_NAME:"))[len("GIFT_NAME:"):].strip()
        
        # Direct, simple response as requested:
        final_text = (
            f"HUH! You're a little too fast, Anushka! You've unlocked the next gift (**{gift_name}**), "
            f"but Harsh has put a **{time_data}** time lock on it! "
            f"Go enjoy your poem and come back later. I'll be waiting! "
        )
        return jsonify({'response_text': final_text, 'agent_state': 'smiling'})

    if current_state_command.startswith("STATUS: DELIVER_NEXT_CLUE."):
        # Direct Python delivery of the clue
        next_clue_question = current_state_command.split("NEXT_QUESTION:")[1].strip()
        final_text = (
            f"Amazing! Time's up, and you're ready for the next surprise! I'm so excited for you!<br>"
            f"Your next challenge is: **{next_clue_question}**"
        )
        return jsonify({'response_text': final_text, 'agent_state': 'excited'})
    
    # 6. Standard LLM Conversation (Used only for clue failures or guardrail violation responses)
    
    full_prompt = f"GAME_MASTER_STATUS: {current_state_command}. USER_INPUT: {user_message}"
    history_contents = [types.Content(role='user', parts=[types.Part(text=full_prompt)])] 
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=history_contents,
            config=AGENT_CONFIG
        )
    except Exception as e:
        return jsonify({'response_text': f"Communication error with Gemini: {e}", 'agent_state': 'confused'})

    final_text = response.text
    
    # --- Defensive check for NoneType ---
    if final_text is None:
        final_text = "Agent Cupid is having a little trouble thinking right now. Please try your message again."
        agent_state = "confused"
    else:
        agent_state = "smiling"
    # --- End check ---
    
    # 7. Enforce Guardrail 
    if 'Uh oh! Harsh didn\'t allow me to do so' in final_text:
        agent_state = "confused"
    
    return jsonify({
        'response_text': final_text.replace('\n', '<br>'),
        'agent_state': agent_state 
    })

if __name__ == '__main__':
    print("--- Starting Agent Server ---")
    print("Go to http://127.0.0.1:5000/")
    app.run(debug=False, use_reloader=False)
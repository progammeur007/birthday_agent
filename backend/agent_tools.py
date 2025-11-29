import datetime
import re

# --- GAME STATE ---
GIFT_UNLOCK_INTERVALS = {
    1: datetime.timedelta(minutes=0),
    2: datetime.timedelta(hours=3),   
    # Add more intervals for gifts 3-6 later!
}

GIFT_STATUS = {
    "clues": [
        {
            "id": 1,
            "sub_state": 0,  # 0=Awaiting Clue Answer, 1=Awaiting Customization Request, 2=Customized
            "gift_name": "The Birthday Bard",
            "clue_question": "What color of dress was Harsh Wearing when you first saw him 😏?",
            # FIX: Use a list of acceptable answers for robust checking
            "expected_answer_list": ["blue", "cyan", "sky blue"],
            "initial_gift_content": (
                "My Dearest Anushka, let this humble verse begin,\n"
                "A tale of when our two small worlds first came within.\n"
                "The night we met, so simple yet so beautifully spun,\n"
                "A quiet tale of destiny,where two souls became one.\n\n"
                "We stayed awake,whisphering into the dark,\n"
                "Every laugh,every word,every cry,striking a tender spark.\n"
                "And then came the moment,gentle as morning dew,\n"
                "When you breathed the words that changed my life-'Love You'\n\n"
                "And look at us now,love,almost a year gone by,\n"
                "My heart still dances whenever you're nearby.\n"
                "My little girl,my joy,you're a year older too,\n"
                "Yet every day feels brand-new,all because of you.\n\n"
                "So let this verse, though clumsy, hold my heart's design,\n"
                "Happy Birthday, my love. Forever yours, and mine."
            ),
            "customization_prompt": (
                "Awesome! You've got the first draft. Now, time for us to reply! How should I change this poem? "
                "Ask me to reply it *funnier*, or *roast Harsh's poetry skills*, or make it *super romantic*! just say reply and the tone you want "
                "If you're happy with it, just tell me: **'I'm done!'**"
            ),
            "current_poem": "", 
        },
        {
            "id": 2,
            "sub_state": 0,
            "gift_name": "The Digital Gallery",
            "clue_question": "What is Harsh's favorite animal that he always promises to get you?",
            "expected_answer_list": ["dog", "pup", "puppy"], 
            "initial_gift_content": "<a href='#' target='_blank'>Click here to view your personalized Digital Photo Album!</a> (Hint: Don't forget to ask me for the next challenge after viewing this!)",
            "customization_prompt": "", 
            "current_poem": "",
        }
    ],
    "completion_timestamps": {
        # Stores completion time as a datetime object: {1: datetime.datetime(2025, 11, 29, 10, 30, 0)}
    },
    "history": [] 
}

# --- HELPER FUNCTION: Time Lock Checker (STABLE) ---

def get_time_status(current_gift_id: int) -> str:
    """Checks if the next gift is time-locked and returns a detailed status."""
    
    next_gift_id = current_gift_id + 1
    
    if next_gift_id > len(GIFT_STATUS["clues"]):
        return "STATUS: ALL_GIFTS_COMPLETE"

    required_interval = GIFT_UNLOCK_INTERVALS.get(next_gift_id)
    completion_time = GIFT_STATUS["completion_timestamps"].get(current_gift_id) 
    
    if not completion_time or not required_interval:
        return "STATUS: ERROR_TIME_LOG_MISSING"

    time_difference = datetime.datetime.now() - completion_time
    
    if time_difference < required_interval:
        time_remaining = required_interval - time_difference
        hours = int(time_remaining.total_seconds() // 3600)
        minutes = int((time_remaining.total_seconds() % 3600) // 60)
        
        return (
            f"STATUS: GIFT_LOCKED_BY_TIME. "
            f"TIME_REMAINING: {hours} hours and {minutes} minutes. "
            f"GIFT_NAME: {GIFT_STATUS['clues'][next_gift_id - 1]['gift_name']}"
        )
    else:
        # Time has passed, unlock the next clue
        GIFT_STATUS["clues"][next_gift_id - 1]["sub_state"] = 0 # Set the new gift to active
        return f"STATUS: DELIVER_NEXT_CLUE. NEXT_QUESTION: {GIFT_STATUS['clues'][next_gift_id - 1]['clue_question']}"

# --- CORE LOGIC: Determines the next state and builds the LLM prompt ---

def generate_next_agent_prompt(user_input: str) -> str:
    """
    Manages the game state machine and generates the context prompt for the LLM.
    """
    active_gift = next((clue for clue in GIFT_STATUS["clues"] if clue["sub_state"] < 2), None)
    
    if active_gift is None:
        return "STATUS: ALL_GIFTS_COMPLETE. The hunt is over! Deliver the final message and conclude the game."
        
    current_gift_id = active_gift["id"]
    
    # --- REGEX CHECK FOR EXIT COMMAND (State 1) ---
    if active_gift['sub_state'] == 1:
        exit_match = re.search(r"i[' ]?m done|i am done|perfect", user_input.lower())
        if exit_match:
            active_gift["sub_state"] = 2 
            GIFT_STATUS["completion_timestamps"][current_gift_id] = datetime.datetime.now() 
            return get_time_status(current_gift_id)

    # State 0: AWAITING CLUE ANSWER
    if active_gift['sub_state'] == 0:
        normalized_input = user_input.lower().strip().replace(" ", "")
        
        # Check if normalized input matches any item in the list
        if normalized_input in [ans.lower().replace(" ", "") for ans in active_gift["expected_answer_list"]]:
            active_gift["sub_state"] = 1 
            active_gift["current_poem"] = active_gift["initial_gift_content"] 
            
            # If the gift is simple (Gift 2+), bypass customization
            if active_gift['id'] > 1:
                active_gift["sub_state"] = 2
                GIFT_STATUS["completion_timestamps"][active_gift["id"]] = datetime.datetime.now()
                return get_time_status(current_gift_id) 

            return (
                f"STATUS: SUCCESS_UNLOCK. "
                f"INITIAL_CONTENT: {active_gift['initial_gift_content']}. "
                f"CUSTOMIZATION_PROMPT: {active_gift['customization_prompt']}"
            )
        else:
            return f"STATUS: FAILURE_CLUE. The user guessed '{user_input}'. The current question is: {active_gift['clue_question']}. Give them a small, non-obvious hint."

    # State 1: AWAITING CUSTOMIZATION REQUEST (LLM Generation)
    elif active_gift['sub_state'] == 1:
        if "next" in user_input.lower() or "challenge" in user_input.lower() or "gift" in user_input.lower():
            return "STATUS: GUARDRAIL_VIOLATION. The user asked for the next step/gift. Enforce the guardrail rule."
        
        # SUCCESS: User is providing a customization request. Trigger LLM call in app.py.
        customization_prompt = (
            f"You are a funny and romantic rewrite specialist. Rewrite the poem entirely based on the user's request. It MUST be a reply to Harsh's poem. "
            f"If the user asks to 'roast Harsh,' make the roast **funny and affectionate,** NEVER mean or dismissive. "
            f"The final poem MUST be concise, under 8 lines, and suitable for a cheerful chat interface. "
            f"Current Poem (Modify This):\n---\n{active_gift['current_poem']}\n-\n"
            f"User Request: {user_input}"
        )
        return f"AGENT_COMMAND: GENERATE_TEXT: PROMPT: {customization_prompt}"

    # State 2: CUSTOMIZED/UNLOCKED (User must ask for the next step)
    elif active_gift['sub_state'] == 2:
        return get_time_status(current_gift_id)

    return "STATUS: UNKNOWN. Prompt the user for what they want to do next."
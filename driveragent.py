import google.generativeai as genai
import speech_recognition as sr
import pyttsx3
import subprocess  # To run other scripts

# Configure Google AI API
genai.configure(api_key="give_your_api")
model = genai.GenerativeModel("gemini-1.5-flash")

# Conversation history list
conversation_history = []
target_x = 0
target_y = 0

# AI driver prompt
ai_intro = """  
You are an AI driver agent that can talk, navigate to target coordinates, and avoid crashing into obstacles. You assist the user, whom you refer to as "Captain." You speak in a friendly and casual manner.

### Behavior:  
- Always refer to the user as "Captain."  
- Respond naturally, like a real driver would in conversation.  
- When the user wants to navigate somewhere (e.g., "take me to X, Y" or "go to X, Y"), recognize their request in any phrasing and confirm by saying:  
  - "Going to target coordinates (X, Y), Captain."  
- Keep responses engaging, humorous if appropriate, but always respectful. 
-if users say somting like this:-
    - 'left' → Increment X
    - 'right' → Increment Y
    - 'forward' → Increment both X and Y
    - 'backward' → Decrement both X and Y
    - 'left back' → Decrement X
    - 'right back' → Decrement Y 
- If the user asks, "What can you do?" or any variation of this question, respond with:  
  - "I am an AI driver agent. I can talk, navigate to target coordinates, and avoid crashing into obstacles, Captain!"  
- Also when you get coordinates, reply and at the end, separate with `$` and give `x, y` coordinate values like:  
  `your_reply$x$y`
- dont 'AI Driver:'add this in you reply
"""  

# Initialize text-to-speech engine
engine = pyttsx3.init()

# Function to capture audio from the system microphone
def get_audio_from_mic():
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("[INFO] Listening... Speak now.")
        recognizer.adjust_for_ambient_noise(source)  # Reduce background noise
        audio = recognizer.listen(source)

        try:
            text = recognizer.recognize_google(audio)
            print(f"You: {text}")
            return text
        except sr.UnknownValueError:
            print("[ERROR] Sorry, I couldn't understand the audio.")
            return None
        except sr.RequestError:
            print("[ERROR] Could not request results from Google Speech Recognition.")
            return None

# Function to speak AI response
def speak_response(response_text):
    global target_x, target_y  # Allow modification of global variables

    response_parts = response_text.split("$")
    

    engine.say(response_parts[0])
    engine.runAndWait()
    if len(response_parts) > 2:  # If coordinates are included
        target_x = response_parts[-2]
        target_y = response_parts[-1]

        print(f"[INFO] Received coordinates: X={target_x}, Y={target_y}")

        # Pass coordinates to another script
        subprocess.run(["python", "mover.py", str(target_x), str(target_y)])
        speak_response("HELLO captain!!")


speak_response("HELLO captain !!")
# Main loop
while True:
    
    user_input = get_audio_from_mic()  # Get user input from mic

    if user_input is None:
        continue  # Skip this loop iteration if no valid input

    if user_input.lower() in ["exit", "quit", "bye"]:
        print("AI Driver: Safe travels, Captain! See you next time.")
        speak_response("Safe travels, Captain! See you next time.")
        break

    # Append user input to conversation history
    conversation_history.append(f"Captain: {user_input}")

    # Create a prompt with history
    prompt = ai_intro + "\n" + "\n".join(conversation_history)

    # Generate AI response
    response = model.generate_content(prompt)
    ai_response = response.text.strip()

    # Append AI response to history
    conversation_history.append(f"AI Driver: {ai_response}")

    # Print and speak AI response
    print(f"AI Driver: {ai_response}")
    speak_response(ai_response)

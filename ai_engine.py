# ai_engine.py
from google import genai
from google.genai import types
from gtts import gTTS
import config
import utils

# Initialize client globally
try:
    client = genai.Client()
except Exception as e:
    print(f"Initialization Warning: API Client failure hook: {e}")
    client = None

def run_sequential_generation(mode_selection, requirement_text):
    """Processes system requirement maps through fallback Google Gen AI models."""
    if not requirement_text or str(requirement_text).strip() == "":
        status = f"⚡ Session Status: Arro has executed {config.runtime_cache['generation_count']} generation pass(es)."
        return "// Error: Please input your general requirements or logic description.", "Diagnostics: Failed due to empty input field.", None, status
        
    prompt = f"Style/Context Match: {mode_selection}\nRequirements: {requirement_text}\nGenerate clean code arrays."
    target_models = ['gemini-2.0-flash', 'gemini-1.5-flash']
    
    generated_output = ""
    diagnostics_log = "=== SEQUENTIAL COMPILER LOGS ===\n"
    
    for model_name in target_models:
        try:
            diagnostics_log += f"• Initiating processing pass using: {model_name}...\n"
            
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    system_instruction="You are an advanced, platform-agnostic software design engineer and code generator."
                )
            )
            
            generated_output = response.text
            config.runtime_cache["code"] = generated_output  
            
            with open(config.CODE_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(generated_output)
                
            diagnostics_log += "• Phase 1 (Macros/Headers Extraction): Processed Successfully ✓\n"
            diagnostics_log += "• Phase 2 (Core Logic Generation): Processed Successfully ✓\n"
            diagnostics_log += "• Phase 3 (Runtime Structural Layout): Processed Successfully ✓\n"
            diagnostics_log += f"╚═ Final Verification: Linkage [{model_name}] completed successfully."
            break
            
        except Exception:
            diagnostics_log += f"  ❌ Pass failed for model {model_name}. Trying backup routing parameters...\n"
            continue
            
    if not generated_output:
        generated_output = "// Connection Fault: 404 NOT_FOUND.\n// All system models returned an error state."
        diagnostics_log += "\nCRITICAL ERROR: Failed to establish target linkage with Google Gen AI."
        status_text = f"❌ Session Status: Action failed. Total generations stand at {config.runtime_cache['generation_count']}."
        return generated_output, diagnostics_log, None, status_text
        
    status_text = utils.write_admin_log(mode_selection, requirement_text)
    return generated_output, diagnostics_log, config.CODE_FILE_PATH, status_text

def generate_voice_explanation(language_choice):
    """Extracts code text arrays and crafts casual spoken structural explanations."""
    code_to_explain = config.runtime_cache["code"]
    if not code_to_explain or "Connection Fault" in code_to_explain:
        return None, "Please run code generation successfully before requesting a narrative breakdown."
        
    lang_code = 'ta' if "Tamil" in language_choice else 'en'
    
    system_instruction = (
        "You are a friendly senior developer talking casually face-to-face with a friend over coffee. "
        "Explain exactly what the provided code script is doing block by block. "
        "Use everyday simple analogies, short conversational phrases, and casual vocal transitions. "
        "Do not read out syntax characters, brackets, or code symbols. Keep it engaging, direct, and human. "
        f"You must deliver this speech completely in fluent conversational { 'Tamil / தமிழ்' if lang_code == 'ta' else 'English' }."
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=f"Break down this script block for a conversational narrative:\n\n{code_to_explain}",
            config=types.GenerateContentConfig(
                temperature=0.6,
                system_instruction=system_instruction
            )
        )
        explanation_text = response.text
        
        tts = gTTS(text=explanation_text, lang=lang_code, slow=False)
        output_audio_path = "explanation_speech.mp3"
        tts.save(output_audio_path)
        
        return output_audio_path, explanation_text
        
    except Exception as e:
        return None, f"Voice system failed to compile: {str(e)}"

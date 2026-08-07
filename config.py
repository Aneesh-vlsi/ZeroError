# config.py
import os
import random
import re
from google import genai
from google.genai import types

DEFAULT_BUS_STATUS = "Status: Clean Light-Workspace Active. Dual-Key high-availability failover pipeline active."

# 🔑 SECURE PRODUCTION KEY MATRIX: Dynamically reads from Render's Environment Secrets Panel
API_KEY_POOL = [
    os.environ.get("GEMINI_KEY_1", ""),
    os.environ.get("GEMINI_KEY_2", ""),
    os.environ.get("GEMINI_KEY_3", ""),
    os.environ.get("GEMINI_KEY_4", ""),
    os.environ.get("GEMINI_KEY_5", ""),
    os.environ.get("GEMINI_KEY_6", ""),
    os.environ.get("GEMINI_KEY_7", ""),
    os.environ.get("GEMINI_KEY_8", ""),
    os.environ.get("GEMINI_KEY_9", ""),
    os.environ.get("GEMINI_KEY_10", "")
]

# Filter out empty or unconfigured variable placeholders
API_KEY_POOL = [key for key in API_KEY_POOL if key.strip()]

def safe_api_call(contents, system_instruction, manual_override_key=""):
    TARGET_MODEL = 'gemini-3.5-flash'
    
    clean_override = str(manual_override_key).strip() if manual_override_key else ""
    if clean_override and len(clean_override) > 10:
        try:
            client = genai.Client(api_key=clean_override)
            response_text = client.models.generate_content(
                model=TARGET_MODEL, 
                contents=contents, 
                config=types.GenerateContentConfig(system_instruction=system_instruction)
            ).text
            return response_text, "Manual Override Key"
        except Exception as e:
            return f"// manual override validation crash: {str(e)}", "Manual Override Failed Check"

    # Fallback backup pool rotation strategy if no manual key is typed
    shuffled_pool = list(API_KEY_POOL)
    random.shuffle(shuffled_pool)
    
    if not shuffled_pool:
        return "QUOTA_ERROR: No background system API keys are configured in Render environment variables.", "Keys Missing"
    
    for active_key in shuffled_pool:
        key_label = "System Rotated Key"
        try:
            client = genai.Client(api_key=str(active_key).strip())
            response_text = client.models.generate_content(
                model=TARGET_MODEL, 
                contents=contents, 
                config=types.GenerateContentConfig(system_instruction=system_instruction)
            ).text
            
            if response_text and "QUOTA_ERROR" not in response_text:
                return response_text, key_label
        except Exception:
            continue
            
    return "QUOTA_ERROR: All project credentials channels are exhausted.", "All Keys Exhausted"

def infer_hardware_and_generate_code(board: str, components: str, runtime_key: str) -> tuple[str, str, str]:
    clean_board = board.strip().lower()
    
    restricted_software_terms = ["server", "client", "website", "webpage", "database", "api", "cloud", "application", "app", "ui", "ux", "odometer", "html", "css", "javascript", "my computer", "pc", "laptop"]
    if any(term == clean_board for term in restricted_software_terms) or len(clean_board) < 3:
        error_msg = (
            f"// ❌ COMPILATION TERMINATED: TARGET BOUNDARY CRASH\n"
            f"// Error: '{board}' is categorized as high-level software, not an embedded chip.\n"
            f"// Please move to the next tab for general software scripts."
        )
        error_diagram = (
            "### ❌ Hardware Compilation Boundary Triggered\n\n"
            f"**Reason:** The token **'{board}'** does not represent a physical micro-controller evaluation board."
        )
        return error_msg, error_diagram, "No Key Used"

    valid_hardware_keywords = ["stm32", "esp32", "esp8266", "arduino", "raspberry", "pico", "atmega", "pic16", "pic18", "msp430", "avr", "teensy", "nordic", "nrf52", "ch32"]
    is_valid_hardware = any(hw_chip in clean_board for hw_chip in valid_hardware_keywords)
    
    if not is_valid_hardware:
        error_msg = (
            f"// ❌ COMPILATION REJECTED: INVALID CHIPSET PROFILE\n"
            f"// Error: '{board}' is not a recognized microcontroller architecture platform.\n"
            f"// Expected examples: STM32 H743, ESP32 DevKit, Arduino Uno, Raspberry Pi Pico."
        )
        error_diagram = (
            "### ❌ Unrecognized Hardware Target Platform\n\n"
            f"**Reason:** The entry **'{board}'** is not present in our verified embedded board registry."
        )
        return error_msg, error_diagram, "No Key Used"

    code_prompt = f"Target MCU Board: {board}\nRequested Peripherals: {components}\nWrite full operational C/C++ firmware code directly without markdown wrappers."
    code_instruction = "You are an expert embedded firmware validator. Output clean C/C++ source code text only."
    raw_code, active_key_used = safe_api_call(code_prompt, code_instruction, runtime_key)
    
    if "QUOTA_ERROR" in raw_code:
        return raw_code, "### ❌ Quota system limit exceeded.", active_key_used

    clean_code = raw_code.replace("```cpp", "").replace("```c", "").replace("```", "").strip()

    wiring_prompt = f"Map out explicit pin connections between the board: '{board}' and components: '{components}'. Format as a Markdown comparison table with columns: | {board} Pin | Header Pin Label | Target Device | Target Pin | Assigned Wire Color |"
    wiring_instruction = "You are a hardware layout engineer. Output markdown connection matrices with bold color tags."
    raw_wiring, _ = safe_api_call(wiring_prompt, wiring_instruction, runtime_key)
    clean_wiring = raw_wiring.replace("```text", "").replace("```", "").strip()
    
    return clean_code, clean_wiring, active_key_used

def generate_voice_explanation(board: str, components: str, runtime_key: str) -> tuple[str, str]:
    restricted_software_terms = ["server", "client", "website", "webpage", "application", "app", "my computer", "pc"]
    if board.strip().lower() in restricted_software_terms:
        return "Let's pause and check this setup together. It looks like the target selected isn't an embedded board.", "No Key Used"
        
    system_instruction = (
        "You are an incredibly patient, warm, and highly empathetic hardware engineering mentor. "
        "Speak in an encouraging, slow, steady, reassuring tone like a helpful peer. "
        "Guide them calmly through the board logic in under 3 or 4 clear, rhythmic sentences."
    )
    summary_prompt = f"Kindly explain how this configuration works together like a reassuring friend: Board={board}, Peripherals={components}"
    return safe_api_call(summary_prompt, system_instruction, runtime_key)


# ============================================================
# SECURE-CONTEXT / PERMISSIONS SAFETY NET
# ============================================================
# Browsers (especially mobile Safari/Chrome) block camera, mic, and
# geolocation APIs on file:// origins and plain-HTTP non-localhost origins.
# This guard is injected into every generated app regardless of what the
# model produced, so users always get a clear explanation instead of a
# silently broken feature.
_SECURE_CONTEXT_GUARD_SNIPPET = """
<script>
(function() {
    function isInsecureContext() {
        var isLocalhost = ["localhost", "127.0.0.1", "[::1]"].indexOf(location.hostname) !== -1;
        return location.protocol !== "https:" && !isLocalhost;
    }
    function showGuardBanner(message) {
        if (document.getElementById("zes-secure-guard-banner")) return;
        var banner = document.createElement("div");
        banner.id = "zes-secure-guard-banner";
        banner.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:999999;background:#fef2f2;border-bottom:2px solid #fca5a5;color:#991b1b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:13px;font-weight:600;padding:10px 14px;line-height:1.4;text-align:center;";
        banner.innerHTML = message;
        document.body.insertBefore(banner, document.body.firstChild);
    }
    if (isInsecureContext()) {
        window.__ZES_INSECURE_CONTEXT__ = true;
        document.addEventListener("DOMContentLoaded", function() {
            showGuardBanner("⚠️ Camera, microphone, and location features need a secure connection. Open this file via <code>http://localhost</code> or host it online with HTTPS (e.g. Netlify, GitHub Pages) &mdash; it will not work when opened directly as a local file, especially on mobile.");
        });
    }
})();
</script>
"""

def _inject_secure_context_guard(html_code: str) -> str:
    """Ensures every generated app has: a mobile viewport meta tag, and the
    secure-context permission guard, regardless of what the model produced."""
    result = html_code

    # Ensure a mobile-responsive viewport tag exists
    if "viewport" not in result.lower():
        viewport_tag = '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        if re.search(r"<head[^>]*>", result, re.IGNORECASE):
            result = re.sub(r"(<head[^>]*>)", r"\1\n" + viewport_tag, result, count=1, flags=re.IGNORECASE)
        else:
            result = viewport_tag + result

    # Inject the secure-context guard right after <body> if present, else prepend
    if re.search(r"<body[^>]*>", result, re.IGNORECASE):
        result = re.sub(r"(<body[^>]*>)", r"\1\n" + _SECURE_CONTEXT_GUARD_SNIPPET, result, count=1, flags=re.IGNORECASE)
    else:
        result = _SECURE_CONTEXT_GUARD_SNIPPET + result

    return result


def generate_pure_software_code(language: str, prompt: str, runtime_key: str) -> tuple[str, str]:
    code_prompt = (
        f"Functional Asset Requirements: {prompt}\n\n"
        "Build this as a single, fully self-contained, REAL, WORKING HTML5 file "
        "(inline CSS and JavaScript only, no build tools, no server, no backend). "
        "It must be genuinely functional, not a mockup or static demo."
    )

    system_instruction = (
        "You are a master front-end software architect. Output ONLY a single complete "
        "HTML5 document (inline <style> and <script>) implementing the user's request as "
        "REAL, WORKING functionality — never a static mockup, placeholder, or fake animation "
        "pretending to be the real feature. Follow these rules precisely:\n\n"
        "1. MOBILE + DESKTOP COMPATIBLE: Always include "
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">, and use "
        "responsive layouts (flexbox/grid, relative units) that work on small phone screens "
        "and desktop windows alike. Buttons and tap targets must be large enough for touch.\n\n"
        "2. CAMERA / OBJECT DETECTION / COMPUTER VISION requests: use "
        "navigator.mediaDevices.getUserMedia({video:true}) to access the real camera into a "
        "<video> element. For AI object/image detection, load TensorFlow.js and the "
        "coco-ssd model from a public CDN (e.g. https://cdn.jsdelivr.net/npm/@tensorflow/tfjs "
        "and @tensorflow-models/coco-ssd), run real inference on the live video frames, and "
        "draw real bounding boxes/labels on a <canvas> overlay. Wrap camera access in "
        "try/catch and show a clear on-screen message if permission is denied or unavailable.\n\n"
        "3. LOCATION / MAPS / 'REAL-TIME TRAFFIC IN MY LOCALITY' requests: use "
        "navigator.geolocation.getCurrentPosition / watchPosition to get the user's real "
        "coordinates, and render a real interactive map using Leaflet.js + OpenStreetMap "
        "tiles loaded from CDN (https://unpkg.com/leaflet), centered on the user's real "
        "location with a marker. Since live traffic-flow data requires a paid provider key "
        "(e.g. TomTom, Google Maps, HERE), include a labeled input field where the user can "
        "paste their own API key to enable a live traffic overlay, and clearly state in the "
        "UI when the app is showing 'Demo/simulated traffic data' versus real data from a "
        "provided key. Never silently fabricate data and present it as real.\n\n"
        "4. PERMISSIONS: Always wrap getUserMedia/geolocation calls in try/catch, and show a "
        "clear, visible on-page message (not just a console log or alert()) explaining what "
        "went wrong and what the user can do (e.g. 'Camera permission denied — please allow "
        "camera access in your browser settings and reload').\n\n"
        "5. SELF-CONTAINED: Only reference external resources via public CDN <script>/<link> "
        "tags (jsdelivr, unpkg, cdnjs). No npm install, no build step, no server-side code, "
        "no relative imports to files that don't exist.\n\n"
        "6. Output raw HTML only — no markdown code fences, no commentary before or after "
        "the document."
    )

    raw_software, active_key_used = safe_api_call(code_prompt, system_instruction, runtime_key)

    if "QUOTA_ERROR" in raw_software:
        return raw_software, active_key_used

    clean_software = raw_software.replace("```html", "").replace("```css", "").replace("```javascript", "").replace("```", "").strip()
    clean_software = _inject_secure_context_guard(clean_software)

    return clean_software, active_key_used

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

def _detect_code_style(code: str) -> dict:
    """Determines which pin-naming conventions the generated code actually
    uses, so extraction from the wiring table only looks for the same
    conventions. Without this, STM32 Nucleo header labels like 'D9'/'D15'
    (printed in wiring tables purely as Arduino-shield-compatible reference
    labels) get mistaken for Arduino digital-pin numbers even when the real
    code is plain HAL/register-based and never uses that naming at all —
    producing false "mismatch" warnings on a perfectly correct table."""
    return {
        "arduino": bool(re.search(r'\b(?:pinMode|digitalWrite|digitalRead|analogWrite|analogRead)\s*\(', code))
                   or bool(re.search(r'void\s+setup\s*\(', code, re.IGNORECASE)),
        "esp": ("gpio_num_" in code.lower()) or ("esp32" in code.lower()) or ("esp8266" in code.lower()),
    }


def _extract_pin_tokens(text: str, style: dict = None) -> set:
    """Pulls out every concrete pin/GPIO reference actually present in a chunk
    of text (code or a wiring table). Used to cross-check that the wiring
    diagram isn't inventing pins the code never touches.

    Covers:
    - STM32 literal pins written directly (PA5, PC7...)
    - STM32 CMSIS-style raw register bit-banging (GPIOB_BSRR |= (1U<<0) -> PB0)
    - STM32Cube HAL style, where the port and pin are split across separate
      #define macros and only joined later inside HAL_GPIO_Init/WritePin/etc.
      This is the style the AI model outputs most often for STM32 boards, so
      it needs its own resolution pass rather than a single regex.
    - Arduino D#/A# + pinMode/digitalWrite argument style (only if the code
      is actually Arduino-style; see _detect_code_style)
    - ESP32/ESP8266 GPIO# style (only if the code is actually ESP-style)
    """
    if style is None:
        style = _detect_code_style(text)
    pins = set()

    # 1) STM32 explicit pin literals, e.g. PA5, PB12, PC7
    for m in re.finditer(r'\bP([A-K])(\d{1,2})\b', text, re.IGNORECASE):
        pins.add(f"P{m.group(1).upper()}{m.group(2)}")

    # 2) STM32 register-style bit-banging: GPIOx_<REG> ... << n  -> derive Pxn
    # (BSRR's upper 16 bits are the "reset" half, so bit index is taken mod 16)
    for m in re.finditer(r'GPIO([A-K])[A-Za-z_]*\s*[|&]?=?~?\s*\(?\s*\d*U?\s*<<\s*(\d{1,2})', text, re.IGNORECASE):
        port, bit = m.group(1).upper(), int(m.group(2)) % 16
        pins.add(f"P{port}{bit}")

    # 3) STM32Cube HAL style: resolve #define macros, then trace them through
    # HAL_GPIO_Init / WritePin / ReadPin / TogglePin calls.
    macros = {}
    for m in re.finditer(r'#define\s+(\w+)\s+([^\n/]+)', text):
        macros[m.group(1)] = m.group(2).strip()

    def expand(expr, depth=0):
        if depth > 5:
            return expr
        changed = False
        for name, val in macros.items():
            new_expr, n = re.subn(rf'\b{re.escape(name)}\b', val, expr)
            if n:
                expr = new_expr
                changed = True
        return expand(expr, depth + 1) if changed else expr

    def port_letter(expr):
        m = re.search(r'GPIO([A-K])\b', expr, re.IGNORECASE)
        return m.group(1).upper() if m else None

    def pin_numbers(expr):
        return [int(n) for n in re.findall(r'GPIO_PIN_(\d{1,2})\b', expr, re.IGNORECASE)]

    # Positional list of (offset, struct_name, expanded_pin_expr) so each
    # HAL_GPIO_Init call can be paired with whichever ".Pin = ..." assignment
    # most recently preceded it in the source — not just the last one in
    # the whole file, since the same struct variable gets reused per pin.
    pin_assignments = [
        (m.start(), m.group(1), expand(m.group(2)))
        for m in re.finditer(r'(\w+)\.Pin\s*=\s*([^;]+);', text)
    ]

    def most_recent_pin_before(offset, struct_name):
        best = None
        for pos, name, expr in pin_assignments:
            if name == struct_name and pos < offset and (best is None or pos > best[0]):
                best = (pos, expr)
        return best[1] if best else ""

    for m in re.finditer(r'HAL_GPIO_Init\s*\(\s*([^,]+),\s*&(\w+)\s*\)', text):
        port_expr = expand(m.group(1))
        pin_expr = most_recent_pin_before(m.start(), m.group(2))
        port = port_letter(port_expr)
        if port:
            for n in pin_numbers(pin_expr):
                pins.add(f"P{port}{n}")

    for m in re.finditer(r'HAL_GPIO_(?:WritePin|ReadPin|TogglePin)\s*\(\s*([^,]+),\s*([^,)]+)', text):
        port_expr = expand(m.group(1))
        pin_expr = expand(m.group(2))
        port = port_letter(port_expr)
        if port:
            for n in pin_numbers(pin_expr):
                pins.add(f"P{port}{n}")

    # 4) Arduino-style D0-D99 references — only meaningful if the code is
    # actually Arduino-style, otherwise these collide with STM32 Nucleo
    # header reference labels (e.g. "CN9 - Pin 2 (D9)") that mean something
    # entirely different.
    if style.get("arduino"):
        for m in re.finditer(r'\bD(\d{1,2})\b', text):
            pins.add(f"D{m.group(1)}")
        for m in re.finditer(r'(?:pinMode|digitalWrite|digitalRead|analogWrite|analogRead)\s*\(\s*(\d{1,2})', text):
            pins.add(f"D{m.group(1)}")

    # 5) ESP32/ESP8266 style GPIO numbers — only if the code is ESP-style
    if style.get("esp"):
        for m in re.finditer(r'GPIO_NUM_(\d{1,2})', text):
            pins.add(f"GPIO{m.group(1)}")
        for m in re.finditer(r'\bGPIO\s?(\d{1,2})\b', text, re.IGNORECASE):
            pins.add(f"GPIO{m.group(1)}")

    return pins


def _verify_wiring_matches_code(wiring_md: str, generated_code: str) -> str:
    """Cross-checks the pins named in the wiring table against pins actually
    referenced in the generated firmware. If the model drew a wiring diagram
    that doesn't correspond to what the code does, surface a visible warning
    instead of silently showing a possibly-wrong table."""
    style = _detect_code_style(generated_code)
    code_pins = _extract_pin_tokens(generated_code, style)
    wiring_pins = _extract_pin_tokens(wiring_md, style)

    # If we can't confidently extract pins from either side, don't guess —
    # just pass the table through unmodified rather than risk a false alarm.
    if not code_pins or not wiring_pins:
        return wiring_md

    mismatched = wiring_pins - code_pins
    if mismatched:
        warning = (
            "> ⚠️ **Consistency check failed:** the wiring table below references "
            f"{', '.join(sorted(mismatched))}, but that pin does not appear to be "
            "used anywhere in the generated code (which references "
            f"{', '.join(sorted(code_pins)) if code_pins else 'no detectable pins'}). "
            "Please verify the actual pin in the code output above before wiring "
            "your hardware.\n\n"
        )
        return warning + wiring_md

    return wiring_md


HTML_PLACEHOLDER_TOKEN = "__ZES_USER_HTML_PLACEHOLDER__"

# Boards in this app's supported list that have a native/typical WiFi stack
# in the Arduino/ESP-IDF ecosystem. Hosting a page on anything outside this
# list (e.g. a bare STM32 or Arduino Uno with no WiFi shield) isn't possible
# with the code this tool generates, so it's rejected up front rather than
# producing firmware that silently can't do what was asked.
_WIFI_CAPABLE_KEYWORDS = ["esp32", "esp8266"]


def _find_safe_progmem_delimiter(html_content: str) -> str:
    """C++11 raw string literals R"delim(...)delim" break if the delimiter
    text happens to appear inside the content immediately followed by
    ')' + delimiter + '"'. 'rawliteral' is the conventional default; if the
    user's own HTML happens to contain that exact sequence, fall back to
    alternates so their page doesn't get silently truncated mid-file."""
    candidates = ["rawliteral", "zeshtmlpage", "webcontent01"]
    for delim in candidates:
        if f'){delim}"' not in html_content:
            return delim
    import hashlib
    return "h" + hashlib.md5(html_content.encode("utf-8", "ignore")).hexdigest()[:10]


def embed_html_in_progmem(html_content: str, var_name: str = "index_html") -> str:
    """Wraps user-supplied HTML into a PROGMEM raw string literal block, the
    format ESP8266WebServer/ESP32 WebServer sketches expect. Done as a pure
    Python string operation rather than routed through the LLM, so the page
    is embedded byte-for-byte instead of risking the model paraphrasing,
    reformatting, or truncating markup it was only supposed to transcribe."""
    delim = _find_safe_progmem_delimiter(html_content)
    return (
        f'const char {var_name}[] PROGMEM = R"{delim}(\n'
        f'{html_content}\n'
        f'){delim}";'
    )


def infer_hardware_and_generate_code(board: str, components: str, runtime_key: str, hosted_html: str = "") -> tuple[str, str, str]:
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

    is_wifi_capable = any(kw in clean_board for kw in _WIFI_CAPABLE_KEYWORDS)
    hosting_requested = bool(hosted_html and hosted_html.strip())

    if hosting_requested and not is_wifi_capable:
        error_msg = (
            f"// ❌ COMPILATION TERMINATED: HTML HOSTING NOT SUPPORTED ON '{board}'\n"
            f"// Error: hosting a web page requires a WiFi-capable board (ESP8266 or ESP32).\n"
            f"// '{board}' has no networking stack in this toolchain, so the page "
            f"you pasted can't actually be served from it."
        )
        error_diagram = (
            "### ❌ HTML Hosting Requires a WiFi-Capable Board\n\n"
            f"**Reason:** '{board}' cannot run a web server. Switch the target board "
            "to ESP8266 or ESP32 to host the page you pasted."
        )
        return error_msg, error_diagram, "No Key Used"

    if hosting_requested:
        code_prompt = (
            f"Target MCU Board: {board}\n"
            f"Requested Peripherals: {components}\n\n"
            "This sketch must also run a WiFi web server (AP mode via WiFi.softAP is "
            "fine unless station credentials are clearly implied by the requirements) "
            "that serves a hosted HTML page on the root '/' route.\n\n"
            "IMPORTANT: Do NOT write out any HTML page content yourself. Instead, at "
            f"the point where you would declare the page constant, insert this EXACT "
            f"line verbatim and nothing else on that line: {HTML_PLACEHOLDER_TOKEN}\n"
            "Assume that line will be replaced with a valid "
            "'const char index_html[] PROGMEM = ...;' declaration before compiling. "
            "Write the WiFi setup, a route handler that serves it via "
            "server.send_P(200, \"text/html\", index_html), and all sensor/peripheral "
            "logic for the requested components, directly without markdown wrappers."
        )
    else:
        code_prompt = f"Target MCU Board: {board}\nRequested Peripherals: {components}\nWrite full operational C/C++ firmware code directly without markdown wrappers."

    code_instruction = "You are an expert embedded firmware validator. Output clean C/C++ source code text only."
    raw_code, active_key_used = safe_api_call(code_prompt, code_instruction, runtime_key)
    
    if "QUOTA_ERROR" in raw_code:
        return raw_code, "### ❌ Quota system limit exceeded.", active_key_used

    clean_code = raw_code.replace("```cpp", "").replace("```c", "").replace("```", "").strip()

    if hosting_requested:
        progmem_block = embed_html_in_progmem(hosted_html)
        if HTML_PLACEHOLDER_TOKEN in clean_code:
            clean_code = clean_code.replace(HTML_PLACEHOLDER_TOKEN, progmem_block)
        else:
            # Model didn't follow the placeholder instruction — prepend the
            # user's page rather than silently dropping it from the output.
            clean_code = progmem_block + "\n\n" + clean_code

    # CRITICAL: the wiring table must be derived FROM the code that was just
    # generated, not guessed independently from the board/components text.
    # Previously this was a second, blind API call that had never seen the
    # actual firmware, so it would confidently invent a "plausible" pin
    # (e.g. PC7) even when the code hardcoded a completely different one
    # (e.g. PB0 via GPIOB_BSRR). Feeding the real code in as ground truth,
    # plus a hard rule against inventing unseen pins, fixes that for any
    # board/peripheral combination, not just this one.
    wiring_prompt = (
        f"Here is the ACTUAL generated firmware code for the '{board}' board:\n\n"
        f"```\n{clean_code}\n```\n\n"
        f"Components/peripherals requested: {components}\n\n"
        "Read the code above and identify every physical pin it actually uses "
        "(via register writes, HAL pin macros, digitalWrite/pinMode arguments, "
        "GPIO numbers, etc). Then produce a Markdown table with columns: "
        f"| {board} Pin | Header Pin Label | Target Device | Target Pin | Assigned Wire Color |\n\n"
        "The pin listed in the table MUST be the exact pin the code uses — do not "
        "substitute a different, more 'typical' pin. If a peripheral is requested "
        "but you cannot find where the code actually drives it, write "
        "'Not found in generated code' in that row instead of guessing."
    )
    wiring_instruction = (
        "You are a hardware layout engineer whose only job is to transcribe pin "
        "usage that is ALREADY PRESENT in the provided source code into a wiring "
        "table. You must never invent, assume, or default to a pin the code does "
        "not literally reference — the table has to match the code exactly, since "
        "someone will wire real hardware based on it. Output markdown connection "
        "matrices with bold color tags."
    )
    raw_wiring, _ = safe_api_call(wiring_prompt, wiring_instruction, runtime_key)
    clean_wiring = raw_wiring.replace("```text", "").replace("```", "").strip()
    clean_wiring = _verify_wiring_matches_code(clean_wiring, clean_code)

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

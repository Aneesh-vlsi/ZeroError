# app.py
import sys
try:
    import gradio as gr
    from app_logic import handle_hardware_pipeline, handle_software_pipeline
    from theme_engine import theme_engine_js, force_light_mode_js, stop_sfx_js, login_wall_css
    from voice_engine import tts_javascript, stop_tts_javascript
except Exception as e:
    print(f"FATAL STARTUP CRASH: {e}")
    sys.exit(1)
import gradio as gr
from app_logic import handle_hardware_pipeline, handle_software_pipeline
from theme_engine import theme_engine_js, force_light_mode_js, stop_sfx_js, login_wall_css
from voice_engine import tts_javascript, stop_tts_javascript
# Add this temporary block right at the very top of app.py


# Client-side processing script that handles custom naming and system-level download location prompts
download_hw_js = """
(file_content) => {
    if (!file_content || file_content.trim() === "") {
        alert("Attention: No compiled blueprint data available to export yet. Please execute compilation first.");
        return;
    }
    let customName = prompt("Enter a filename for your hardware blueprint:", "verified_embedded_blueprint.txt");
    if (!customName) return; 
    if (!customName.toLowerCase().endsWith(".txt")) { customName += ".txt"; }
    let dataBlob = new Blob([file_content], { type: "text/plain;charset=utf-8" });
    let linkElement = document.createElement("a");
    linkElement.href = URL.createObjectURL(dataBlob);
    linkElement.download = customName;
    document.body.appendChild(linkElement);
    linkElement.click();
    document.body.removeChild(linkElement);
}
"""

download_sw_js = """
(file_content) => {
    if (!file_content || file_content.trim() === "") {
        alert("Attention: No compiled software asset data available to export yet. Please execute compilation first.");
        return;
    }
    let customName = prompt("Enter a filename for your software code:", "compiled_application.html");
    if (!customName) return; 
    if (!customName.toLowerCase().endsWith(".html")) { customName += ".html"; }
    let dataBlob = new Blob([file_content], { type: "text/html;charset=utf-8" });
    let linkElement = document.createElement("a");
    linkElement.href = URL.createObjectURL(dataBlob);
    linkElement.download = customName;
    document.body.appendChild(linkElement);
    linkElement.click();
    document.body.removeChild(linkElement);
}
"""

# Client-side logout action script that safely clears HTTP Basic Authentication headers
logout_session_js = """
() => {
    let currentURL = window.location.href;
    let cleanURL = currentURL.replace(/^(https?:\/\/)(.*)/, '$1logout:logout@$2');
    try {
        sessionStorage.clear();
        localStorage.clear();
    } catch(e) {}
    window.location.href = cleanURL;
}
"""

with gr.Blocks() as app:
    with gr.Row(elem_id="header-bar-container", variant="compact"):
        with gr.Column(scale=4):
            gr.Markdown("# 🤖 ZeroError Silicon")
            gr.Markdown("<p style='color: #475569 !important; font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, sans-serif !important; font-size: 15px !important; font-weight: 500 !important; margin: 4px 0 16px 0 !important; padding: 0 !important; line-height: 1.4 !important; letter-spacing: -0.01em !important;'>Next-Generation AI Tooling for Heterogeneous Microcontrollers</p>")
        with gr.Column(scale=1, min_width=120):
            logout_btn = gr.Button("🚪 Log Out", variant="stop", size="sm")

    with gr.Row():
        bus_status_display = gr.Textbox(label="Hardware Bus Tracking Status", value="Status: Workspace Online. Ready to receive design rules.", interactive=False, scale=3)
        theme_selector = gr.Dropdown(
            label="🎨 Select Interface Workspace Theme",
            choices=["Light Slate (Default Clean)", "Ocean Blue Breeze", "Forest Mint", "Sunset Orange & Ember", "Classic Steel Cyber"],
            value="Light Slate (Default Clean)",
            interactive=True,
            scale=2
        )

    with gr.Row():
        voice_persona_dropdown = gr.Dropdown(
            label="🗣️ Select Assistant Voice Profile Persona (Global Control)",
            choices=["May (Clear Female Profile)", "Heera (Indian Accent Female)", "Max (Standard Male Profile)", "Jimmy (Fast Tech Profile)"],
            value="Max (Standard Male Profile)",
            interactive=True
        )
        manual_key_input = gr.Textbox(
            label="🔑 Emergency API Token Manual Override (Optional)",
            placeholder="Paste fresh AQ.Ab8... token here if quota is exhausted...",
            type="password",
            interactive=True
        )

    with gr.Tabs():
        # TAB 1: EMBEDDED HARDWARE FIRMWARE
        with gr.Tab("📟 Embedded Hardware Firmware"):
            gr.Markdown("### Secure Microcontroller Code & Wiring Synthesis Block")
            with gr.Row():
                with gr.Column(scale=1):
                    board_input = gr.Textbox(label="1️⃣ Enter Target Microcontroller Board Name", placeholder="e.g., STM32 H743ZI2, ESP32, Arduino Uno", value="")
                with gr.Column(scale=2):
                    components_input = gr.Textbox(label="2️⃣ Enter Required Sensors, Pins, and Displays Profile", placeholder="e.g., sense distance via ultrasonic sensor and show on oled screen", value="", lines=2)
            
            compile_hw_btn = gr.Button("⚡ Run Multi-Pass Code Compilation & Wire Mapping Pass", variant="primary")
            
            with gr.Row():
                with gr.Column(scale=3):
                    hw_code_output = gr.Code(label="3️⃣ Verified Source Script Code Output", language="cpp", value="")
                    gr.Markdown("### 🔌 6️⃣ Physical Wires & Pin Connection Diagrams (Color Coded Wire Tracks)")
                    with gr.Group():
                        hw_wiring_output = gr.Markdown(value="*Awaiting compilation trigger sequence to map hardware schematics...*")
                    gr.Markdown("---")
                    
                    hw_download_btn = gr.Button("📥 Download Verified Script & Wire Map File Locally", variant="secondary")
                    
                    with gr.Row():
                        hw_play_btn = gr.Button("🔊 Silicon talks", variant="secondary")
                        hw_stop_btn = gr.Button("🛑 Stop Silicon talks", variant="stop")
                    hw_voice_cache = gr.Textbox(visible=False)
                    hw_raw_download_cache = gr.Textbox(visible=False)
                with gr.Column(scale=2):
                    hw_log_output = gr.Textbox(label="Sequential Compilation Diagnostics Log", lines=15, interactive=False)

        # TAB 2: GENERAL APPLICATION CODE DEVELOPMENT (HTML/CSS LAYOUTS ONLY)
        with gr.Tab("💻 General Desktop Code (HTML/CSS)"):
            gr.Markdown("### 💡 Isolated Frontend Engine Workspace\n*This module is strictly dedicated to creating responsive front-end user interface designs using pure interactive HTML, CSS layouts, and client-side JavaScript canvas scripts.*")
            
            with gr.Row():
                sw_prompt_input = gr.Textbox(label="1️⃣ Enter Frontend User Interface Sizing, Theme & Animation Logic Rules", placeholder="e.g., create an interactive analog gauge odometer configuration with sleek animations...", value="", lines=2)
            
            compile_sw_btn = gr.Button("⚙️ Compile Frontend Design Blueprint", variant="primary")
            
            with gr.Row():
                with gr.Column(scale=3):
                    sw_code_output = gr.HTML(label="2️⃣ Live Functional Application Workspace Preview")
                    gr.Markdown("---")
                    
                    # INFORMATIVE USAGE NOTICE
                    gr.HTML(value="""
                        <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px 16px; margin: 10px 0 20px 0; display: flex; align-items: flex-start; gap: 8px;">
                            <span style="color: #2563eb; font-size: 18px; font-weight: bold; line-height: 1.2;">ℹ️</span>
                            <p style="color: #1e3a8a !important; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important; font-size: 13px !important; font-weight: 500 !important; margin: 0 !important; padding: 0 !important; line-height: 1.5 !important;">
                                <strong>How this works:</strong> The preview above runs in a sandboxed frame, so features like camera, microphone, or GPS may be limited here depending on your browser.
                                For full functionality &mdash; especially on mobile &mdash; click <strong>'Download Software Code Locally'</strong>, then either open it via <code>localhost</code> (desktop testing) or host the downloaded file on a free HTTPS service like Netlify or GitHub Pages (required for camera/location access on phones). The app itself will show an on-screen note if it detects it's running somewhere those features can't work.
                            </p>
                        </div>
                    """)
                    
                    sw_download_btn = gr.Button("📥 Download Software Code Locally", variant="secondary")
                    
                    with gr.Row():
                        sw_play_btn = gr.Button("🔊 Silicon talks", variant="secondary")
                        sw_stop_btn = gr.Button("🛑 Stop Silicon talks", variant="stop")
                    sw_voice_cache = gr.Textbox(visible=False)
                    sw_raw_download_cache = gr.Textbox(visible=False)
                with gr.Column(scale=2):
                    sw_log_output = gr.Textbox(label="Application Diagnostics Log", lines=15, interactive=False)

    # ==========================================
    # EVENT LOGIC TRACK WRAPPERS AND ROUTING
    # ==========================================
    
    # Active Log Out Listener Routine
    logout_btn.click(fn=None, inputs=None, js=logout_session_js)
    
    # Dynamic Theme Injector Trigger
    theme_selector.change(fn=None, inputs=[theme_selector], js=theme_engine_js)
    # Apply the selected theme (incl. UI polish) immediately on first page load,
    # not only after the user manually changes the dropdown.
    app.load(fn=None, inputs=[theme_selector], js=theme_engine_js)

    # Hardware Pipeline Trigger Mapping
    compile_hw_btn.click(
        fn=handle_hardware_pipeline,
        inputs=[board_input, components_input, manual_key_input],
        outputs=[hw_log_output, hw_code_output, hw_wiring_output, hw_raw_download_cache, hw_voice_cache, bus_status_display]
    )

    # Hardware Download Pipeline JavaScript Execution
    hw_download_btn.click(fn=None, inputs=[hw_raw_download_cache], js=download_hw_js)

    # Hardware Voice Assistant Management 
    hw_play_btn.click(fn=None, inputs=[voice_persona_dropdown, hw_voice_cache, hw_code_output], js=tts_javascript)
    hw_stop_btn.click(fn=None, inputs=None, js=stop_tts_javascript)

    # Software Pipeline Trigger Mapping
    compile_sw_btn.click(
        fn=handle_software_pipeline,
        inputs=[gr.State("html"), sw_prompt_input, manual_key_input],
        outputs=[sw_log_output, sw_code_output, sw_raw_download_cache, sw_voice_cache, bus_status_display]
    )

    # Software Download Pipeline JavaScript Execution
    sw_download_btn.click(fn=None, inputs=[sw_raw_download_cache], js=download_sw_js)

    # Software Voice Assistant Management
    sw_play_btn.click(fn=None, inputs=[voice_persona_dropdown, sw_voice_cache, sw_raw_download_cache], js=tts_javascript)
    sw_stop_btn.click(fn=None, inputs=None, js=stop_tts_javascript)

import os # Make sure this is added to fetch environment variables

if __name__ == "__main__":
    app.launch(
        auth=("ZeroError", "123456"),
        auth_message="Please log in with your authorized Arro engine credentials.",
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)), # <--- CRITICAL FIX
        theme=gr.themes.Default(),
        js=force_light_mode_js,
        css=login_wall_css,
        ssr_mode=False
    )

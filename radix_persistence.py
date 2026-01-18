# radix_persistence.py
# Smart Persistence: Robust Sandbox Escape

import streamlit as st
from streamlit.components.v1 import html as st_html
import urllib.parse

class SessionPersistence:
    """Manages browser-based session persistence"""
    
    # 1. AUTO-SAVE SCRIPT (Invisible)
    @staticmethod
    def get_auto_save_script(char: str) -> str:
        safe_char = char or ""
        return f"""
        <script>
            try {{
                localStorage.setItem('radix_last_char', '{safe_char}');
            }} catch (e) {{ console.error('Save failed', e); }}
        </script>
        """

    # 2. RESUME BUTTON (Robust Navigation)
    @staticmethod
    def get_resume_component(base_url: str) -> str:
        # Heartbeat script
        heartbeat_script = f"""
        <script>
            (function() {{
                setInterval(() => {{
                    fetch(window.location.href, {{method: 'GET'}}).catch(e => {{}});
                }}, 45000);
            }})();
        </script>
        """
        
        return f"""
        <div id="radix-resume-wrapper" style="text-align:center; margin-top:20px; display:none;">
            <a id="radix-resume-link" href="#" style="
                text-decoration: none;
                background-color: #ffffff;
                color: #d35400;
                border: 2px solid #d35400;
                padding: 12px 25px;
                border-radius: 8px;
                font-weight: 700;
                font-family: sans-serif;
                font-size: 16px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transition: all 0.2s;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                cursor: pointer;
            ">
                🔄 Resume Previous Session
            </a>
            <div style="font-size: 0.85em; color: #666; margin-top: 8px;">
                Recovered from browser storage
            </div>
        </div>
        <script>
            (function() {{
                try {{
                    const saved = localStorage.getItem('radix_last_char');
                    if (saved && saved.length === 1 && saved !== 'null') {{
                        const link = document.getElementById('radix-resume-link');
                        const wrapper = document.getElementById('radix-resume-wrapper');
                        
                        // Construct URL
                        const baseUrl = "{base_url}".replace(/\\/$/, "");
                        const fullUrl = baseUrl + "/?c=" + encodeURIComponent(saved);
                        
                        link.href = fullUrl;
                        link.innerHTML = "🔄 Resume Session: " + saved;
                        wrapper.style.display = "block";
                        
                        // CLICK HANDLER: Try Top Nav -> Fallback to New Tab
                        link.onclick = function(e) {{
                            e.preventDefault();
                            link.innerHTML = "⌛ Loading...";
                            link.style.opacity = "0.7";
                            
                            try {{
                                // Attempt 1: Navigate current tab
                                window.top.location.href = fullUrl;
                            }} catch (err) {{
                                console.log("Top nav blocked, opening new tab");
                                // Attempt 2: Open new tab (sandbox usually allows this)
                                window.open(fullUrl, '_blank');
                                // Reset button text
                                setTimeout(() => {{
                                    link.innerHTML = "🔄 Resume Session: " + saved;
                                    link.style.opacity = "1";
                                }}, 1000);
                            }}
                        }};
                    }}
                }} catch (e) {{ console.error('Resume error', e); }}
            }})();
        </script>
        {heartbeat_script}
        """

    @staticmethod
    def get_heartbeat_component() -> str:
        return """
        <script>
            setInterval(() => {
                fetch(window.location.href, {headers: {'Cache-Control': 'no-cache'}}).catch(()=>{});
            }, 45000);
        </script>
        """

class PersistenceManager:
    """Main persistence manager"""
    
    def __init__(self, state_manager):
        self.state = state_manager
    
    # HARDCODED APP URL
    BASE_URL = "https://chinese-5n7qfcqoljkixr2spprdbr.streamlit.app"
    
    def auto_save(self):
        char = self.state.get_selected_component()
        if char:
            st_html(SessionPersistence.get_auto_save_script(char), height=0)
    
    def try_restore(self):
        if self.state.get_selected_component():
            return

        char_param = st.query_params.get("c")
        if char_param:
            from radix_state import InputValidator
            validated = InputValidator.validate_character_input(char_param)
            if validated:
                self.state.complete_startup()
                self.state.complete_onboarding()
                self.state.enter_character_view(validated)
                st.toast(f"Restored from URL: {validated}", icon="🔄")
    
    def show_resume_option(self):
        st_html(SessionPersistence.get_resume_component(self.BASE_URL), height=100)
        
    def add_heartbeat(self):
        st_html(SessionPersistence.get_heartbeat_component(), height=0)

    def render_controls(self):
        with st.expander("💾 Connection Status", expanded=False):
            st.caption("✅ URL Persistence Active")
            if st.button("🗑️ Clear Local History", use_container_width=True):
                st_html("<script>localStorage.removeItem('radix_last_char');</script>", height=0)
                st.toast("History cleared")

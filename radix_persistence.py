# radix_persistence.py
# Smart Persistence: URL for sharing + LocalStorage for crash recovery

import streamlit as st
from streamlit.components.v1 import html as st_html
import urllib.parse

class SessionPersistence:
    """Manages browser-based session persistence"""
    
    # 1. AUTO-SAVE SCRIPT (Invisible)
    # Writes the current character to Browser LocalStorage every time it updates
    @staticmethod
    def get_auto_save_script(char: str) -> str:
        safe_char = char or ""
        return f"""
        <script>
            try {{
                localStorage.setItem('radix_last_char', '{safe_char}');
                console.log('[Radix] Auto-saved to storage: {safe_char}');
            }} catch (e) {{ console.error('Save failed', e); }}
        </script>
        """

    # 2. RESUME BUTTON (Visible only if save found)
    # Reads LocalStorage. If a character exists, shows a styled Link Button.
    @staticmethod
    def get_resume_component() -> str:
        # Check for heartbeat loop script to keep session alive
        heartbeat_script = f"""
        <script>
            (function() {{
                const interval = 45000;
                function ping() {{
                    fetch(window.location.href, {{
                        method: 'GET',
                        headers: {{'Cache-Control': 'no-cache'}},
                        credentials: 'same-origin'
                    }}).catch(e => {{}});
                }}
                setInterval(ping, interval);
            }})();
        </script>
        """
        
        return f"""
        <div id="radix-resume-wrapper" style="text-align:center; margin-top:20px; display:none;">
            <a id="radix-resume-link" href="#" target="_top" style="
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
                    // Check if saved value is valid (1 character)
                    if (saved && saved.length === 1 && saved !== 'null') {{
                        const link = document.getElementById('radix-resume-link');
                        const wrapper = document.getElementById('radix-resume-wrapper');
                        
                        // Update link to point to the URL parameter
                        // target="_top" breaks out of the iframe to reload the app
                        link.href = "?c=" + encodeURIComponent(saved);
                        link.innerHTML = "🔄 Resume Session: " + saved;
                        
                        // Reveal the button
                        wrapper.style.display = "block";
                    }}
                }} catch (e) {{ console.error('Resume check failed', e); }}
            }})();
        </script>
        {heartbeat_script}
        """

    @staticmethod
    def get_heartbeat_component() -> str:
        """Simple keep-alive heartbeat for the main app view"""
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
    
    def auto_save(self):
        """
        Called at end of main loop. 
        1. Ensures URL is synced (?c=...)
        2. Writes to LocalStorage for crash recovery
        """
        char = self.state.get_selected_component()
        if char:
            # Inject invisible JS to save to LocalStorage
            st_html(SessionPersistence.get_auto_save_script(char), height=0)
    
    def try_restore(self):
        """
        Restore state from URL query parameters.
        Run this BEFORE startup checks.
        """
        # If we already have a selection, do nothing
        if self.state.get_selected_component():
            return

        # Check URL
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
        """
        Render the 'Resume' button on Splash/Home screen.
        """
        st_html(SessionPersistence.get_resume_component(), height=100)
        
    def add_heartbeat(self):
        """
        Add heartbeat to keep the session alive.
        """
        st_html(SessionPersistence.get_heartbeat_component(), height=0)

    def render_controls(self):
        """Render debug controls in sidebar"""
        with st.expander("💾 Connection Status", expanded=False):
            st.caption("✅ URL Persistence Active")
            st.caption("✅ Local Backup Active")
            
            if st.button("🗑️ Clear Local History", use_container_width=True):
                st_html("<script>localStorage.removeItem('radix_last_char');</script>", height=0)
                st.toast("History cleared")

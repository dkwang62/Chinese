# radix_persistence.py
# URL-based session persistence

import streamlit as st
from streamlit.components.v1 import html as st_html
import json
import hashlib

class SessionPersistence:
    """Manages browser-based session persistence"""
    
    # Keeping the heartbeat to ensure session doesn't expire too quickly
    HEARTBEAT_INTERVAL = 45000
    
    @staticmethod
    def get_heartbeat_component() -> str:
        """Keep session alive with heartbeat"""
        return f"""
        <div id="radix-heartbeat" style="
            position: fixed; bottom: 10px; right: 10px;
            background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
            color: white; padding: 8px 16px; border-radius: 24px;
            font-size: 12px; font-weight: 700; z-index: 9999;
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
            display: none; font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        ">💚 Session Active</div>
        <script>
            (function() {{
                const el = document.getElementById('radix-heartbeat');
                let count = 0;
                function ping() {{
                    count++;
                    fetch(window.location.href, {{
                        method: 'GET',
                        headers: {{'Cache-Control': 'no-cache'}},
                        credentials: 'same-origin'
                    }}).then(() => {{
                        console.log(`💚 [Radix] Heartbeat #${{count}}`);
                        el.textContent = `💚 Active (ping #${{count}})`;
                        el.style.display = 'block';
                        setTimeout(() => el.style.display = 'none', 2000);
                    }});
                }}
                setInterval(ping, {SessionPersistence.HEARTBEAT_INTERVAL});
                setTimeout(ping, 5000);
            }})();
        </script>
        """

class PersistenceManager:
    """Main persistence manager"""
    
    def __init__(self, state_manager):
        self.state = state_manager
    
    def auto_save(self):
        """
        No-op for URL persistence.
        State is saved implicitly when enter_character_view updates the URL.
        """
        pass
    
    def try_restore(self):
        """
        Restore state from URL query parameters.
        This runs server-side before the UI renders, avoiding iframe redirects.
        """
        # If we have already selected a component in this run, don't override
        if self.state.get_selected_component():
            return

        # Check URL for 'c' parameter (character)
        char_param = st.query_params.get("c")
        
        if char_param:
            # Use local import to avoid circular dependency
            from radix_state import InputValidator
            
            validated = InputValidator.validate_character_input(char_param)
            if validated:
                # 1. Mark system as "ready" to bypass splash screens
                self.state.complete_startup()
                self.state.complete_onboarding()
                
                # 2. Enter the character view immediately
                # This sets selected_comp, show_inputs=False, etc.
                self.state.enter_character_view(validated)
                
                st.toast(f"restored: {validated}", icon="🔄")
    
    def add_heartbeat(self):
        """Add heartbeat"""
        if self.state.is_onboarding_complete():
            st_html(SessionPersistence.get_heartbeat_component(), height=0)
    
    def render_controls(self):
        """Render controls (Simplified for URL mode)"""
        with st.expander("💾 Session Persistence", expanded=False):
            st.info("State is now saved automatically in your browser's address bar (URL).")
            st.caption("Bookmark or share the current URL to return to this specific character.")
            
            current_c = st.query_params.get("c", "None")
            st.code(f"Current URL Parameter: ?c={current_c}", language="text")
            
            if st.button("🗑️ Reset to Home", use_container_width=True):
                self.state.go_to_root()
                st.rerun()

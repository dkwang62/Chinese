# radix_persistence.py
# URL-based session persistence with Clickable Links

import streamlit as st
from streamlit.components.v1 import html as st_html
import urllib.parse

class SessionPersistence:
    """Manages browser-based session persistence"""
    
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
    
    # Your specific app domain
    BASE_URL = "https://chinese-5n7qfcqoljkixr2spprdbr.streamlit.app/"
    
    def auto_save(self):
        """No-op for URL persistence."""
        pass
    
    def try_restore(self):
        """Restore state from URL query parameters."""
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
                st.toast(f"Restored: {validated}", icon="🔄")
    
    def add_heartbeat(self):
        """Add heartbeat"""
        if self.state.is_onboarding_complete():
            st_html(SessionPersistence.get_heartbeat_component(), height=0)
    
    def render_controls(self):
        """Render controls with CLICKABLE buttons"""
        with st.expander("🔗 Share & Save", expanded=False):
            st.info("State is saved in the URL.")
            
            # 1. Get current char
            current_c = st.query_params.get("c")
            if not current_c:
                current_c = self.state.get_selected_component()

            # 2. Generate Clickable Link
            if current_c:
                param = urllib.parse.urlencode({'c': current_c})
                full_url = f"{self.BASE_URL}?{param}"
                
                # Renders a clickable button that opens the link
                st.link_button(
                    label=f"🔗 Open {current_c} in New Tab", 
                    url=full_url, 
                    use_container_width=True
                )
                
                # Also show code for copying if needed
                st.caption("Or copy raw link:")
                st.code(full_url, language="text")
            else:
                st.link_button("🏠 Open Home Page", self.BASE_URL, use_container_width=True)
            
            st.markdown("---")
            if st.button("🗑️ Reset / Go Home", use_container_width=True):
                self.state.go_to_root()
                st.rerun()

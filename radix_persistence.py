# radix_persistence.py
# URL-based persistence with localStorage backup

import streamlit as st
from streamlit.components.v1 import html as st_html

class SessionPersistence:
    """Clean URL-based persistence"""
    
    @staticmethod
    def get_auto_save_script(char: str) -> str:
        """Save to localStorage as backup"""
        return f"""<script>
try {{ localStorage.setItem('radix_last', '{char or ""}'); }}
catch(e) {{ console.log('Save skipped'); }}
</script>"""
    
    @staticmethod
    def get_resume_button(base_url: str) -> str:
        """Smart resume button that reads localStorage"""
        return f"""
<div id="resume-container" style="text-align:center; margin:25px 0; display:none;">
    <a id="resume-link" href="#" style="
        display: inline-flex; align-items: center; gap: 10px;
        padding: 14px 28px; border-radius: 12px;
        background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
        color: white; text-decoration: none; font-weight: 700;
        font-size: 16px; box-shadow: 0 4px 12px rgba(76,175,80,0.3);
        transition: all 0.2s ease; border: 2px solid #2e7d32;
    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(76,175,80,0.4)';"
       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(76,175,80,0.3)';">
        <span style="font-size:24px;">🔄</span>
        <span id="resume-text">Resume Session</span>
    </a>
    <div style="font-size:13px; color:#666; margin-top:8px;">Last viewed character</div>
</div>
<script>
(()=>{{
    try {{
        const saved = localStorage.getItem('radix_last');
        if (!saved || saved.length !== 1) return;
        
        const link = document.getElementById('resume-link');
        const text = document.getElementById('resume-text');
        const container = document.getElementById('resume-container');
        
        // Build URL
        const url = '{base_url}'.replace(/\/$/, '') + '/?c=' + encodeURIComponent(saved);
        link.href = url;
        text.textContent = 'Resume: ' + saved;
        container.style.display = 'block';
        
        // Handle click
        link.onclick = (e) => {{
            e.preventDefault();
            text.textContent = 'Loading...';
            try {{ window.top.location.href = url; }}
            catch(err) {{ window.open(url, '_blank'); }}
        }};
    }} catch(e) {{ console.log('Resume unavailable'); }}
}})();
</script>"""
    
    @staticmethod
    def get_heartbeat() -> str:
        """Lightweight heartbeat"""
        return """<script>
setInterval(()=>fetch(window.location.href,{headers:{'Cache-Control':'no-cache'}}).catch(()=>{}),45000);
</script>"""


class PersistenceManager:
    """Minimal persistence manager"""
    
    def __init__(self, state_manager):
        self.state = state_manager
        self.base_url = st.secrets.get("app", {}).get(
            "base_url", 
            "https://chinese-5n7qfcqoljkixr2spprdbr.streamlit.app"
        )
    
    def auto_save(self):
        """Save current character to localStorage as backup"""
        char = self.state.get_selected_component()
        if char and not self.state.is_showing_inputs():
            st_html(SessionPersistence.get_auto_save_script(char), height=0)
    
    def try_restore(self):
        """Check URL param ?c= and restore if present"""
        # Skip if already viewing a character
        if self.state.get_selected_component():
            return
        
        # Check URL for ?c=水
        char_param = st.query_params.get("c")
        if not char_param:
            return
        
        # Validate the character
        from radix_state import InputValidator
        validated = InputValidator.validate_character_input(char_param)
        
        if validated:
            # Deep restore: skip all startup screens
            self.state.state["startup_file_choice_made"] = True
            self.state.state["onboarding_done"] = True
            
            # Navigate to character
            self.state.enter_character_view(validated)
            
            st.toast(f"📍 Restored: {validated}", icon="✅")
    
    def show_resume_option(self):
        """Show resume button on splash screen"""
        st_html(SessionPersistence.get_resume_button(self.base_url), height=110)
    
    def add_heartbeat(self):
        """Add invisible heartbeat"""
        if self.state.is_onboarding_complete():
            st_html(SessionPersistence.get_heartbeat(), height=0)
    
    def render_controls(self):
        """Minimal status in sidebar"""
        with st.expander("💾 Session Status", expanded=False):
            char = self.state.get_selected_component()
            
            if char:
                st.success(f"📍 Current: **{char}**")
                st.caption("✅ URL bookmark active")
                st.caption("✅ Heartbeat running")
            else:
                st.info("Navigate to a character to enable persistence")
            
            st.markdown("---")
            
            if st.button("🗑️ Clear History", use_container_width=True):
                st_html("<script>localStorage.removeItem('radix_last');</script>", height=0)
                st.toast("History cleared")
            
            with st.expander("ℹ️ How It Works"):
                st.caption("""
                **URL Persistence:**
                - Characters update the URL (e.g., `?c=水`)
                - Share/bookmark URLs to save positions
                - Browser back button navigates history
                
                **Backup Storage:**
                - Last character saved to localStorage
                - Resume button appears on splash screen
                - Survives browser restarts
                """)

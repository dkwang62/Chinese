# radix_persistence.py
# Simplified session persistence with VISIBLE confirmation

import streamlit as st
from streamlit.components.v1 import html as st_html
import json
import hashlib

class SessionPersistence:
    """Manages browser-based session persistence and heartbeat"""
    
    PERSISTENT_KEYS = [
        "selected_comp", "last_valid_selected_comp", "history", "show_inputs",
        "display_mode", "stroke_range", "radical", "component_idc",
        "script_filter", "grid_sort_mode", "grid_script_filter",
        "page", "derivative_page", "onboarding_done", "startup_file_choice_made",
        "preview_comp", "text_input_comp", "fav_cursor"
    ]
    
    STORAGE_KEY = "radix_session_v1"
    HEARTBEAT_INTERVAL = 45000  # 45 seconds
    
    @staticmethod
    def save_to_browser(session_state) -> str:
        """Save session state to localStorage with visible console logs"""
        snapshot = {}
        for key in SessionPersistence.PERSISTENT_KEYS:
            if key in session_state:
                value = session_state[key]
                try:
                    json.dumps(value)
                    snapshot[key] = value
                except (TypeError, ValueError):
                    pass
        
        state_json = json.dumps(snapshot)
        state_hash = hashlib.md5(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()[:8]
        
        # Get current character for logging
        current_char = snapshot.get('selected_comp', 'none')
        
        return f"""
        <script>
            (function() {{
                try {{
                    const stateData = {json.dumps(state_json)};
                    const stateHash = "{state_hash}";
                    const currentChar = "{current_char}";
                    const timestamp = new Date().toLocaleTimeString();
                    
                    localStorage.setItem('{SessionPersistence.STORAGE_KEY}', stateData);
                    localStorage.setItem('{SessionPersistence.STORAGE_KEY}_hash', stateHash);
                    localStorage.setItem('{SessionPersistence.STORAGE_KEY}_char', currentChar);
                    localStorage.setItem('{SessionPersistence.STORAGE_KEY}_time', timestamp);
                    
                    console.log('âœ… [Radix] Saved session at ' + timestamp);
                    console.log('   Character: ' + currentChar);
                    console.log('   Hash: ' + stateHash);
                }} catch (e) {{
                    console.error('â�� [Radix] Save failed:', e);
                }}
            }})();
        </script>
        """
    
    @staticmethod
    def get_heartbeat_component() -> str:
        """Heartbeat that keeps session alive and shows status"""
        return f"""
        <div id="radix-heartbeat" style="
            position: fixed;
            bottom: 10px;
            right: 10px;
            background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
            color: white;
            padding: 8px 16px;
            border-radius: 24px;
            font-size: 12px;
            font-weight: 700;
            z-index: 9999;
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
            display: none;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            transition: all 0.3s ease;
        ">
            💚 Keeping session alive...
        </div>
        
        <script>
            (function() {{
                const heartbeatEl = document.getElementById('radix-heartbeat');
                let heartbeatCount = 0;
                
                function showHeartbeat(msg) {{
                    heartbeatEl.textContent = msg;
                    heartbeatEl.style.display = 'block';
                    setTimeout(() => {{
                        heartbeatEl.style.display = 'none';
                    }}, 3000);
                }}
                
                function sendHeartbeat() {{
                    heartbeatCount++;
                    const time = new Date().toLocaleTimeString();
                    
                    fetch(window.location.href, {{
                        method: 'GET',
                        headers: {{'Cache-Control': 'no-cache'}},
                        credentials: 'same-origin'
                    }})
                    .then(() => {{
                        console.log(`💚 [Radix] Heartbeat #${{heartbeatCount}} at ${{time}}`);
                        showHeartbeat(`💚 Session Active (ping #${{heartbeatCount}})`);
                    }})
                    .catch(e => {{
                        console.warn(`â�› [Radix] Heartbeat #${{heartbeatCount}} failed:`, e);
                    }});
                }}
                
                // Heartbeat every {SessionPersistence.HEARTBEAT_INTERVAL}ms
                setInterval(sendHeartbeat, {SessionPersistence.HEARTBEAT_INTERVAL});
                
                // Initial heartbeat after 5 seconds
                setTimeout(() => {{
                    sendHeartbeat();
                    console.log('âœ… [Radix] Heartbeat system started');
                }}, 5000);
            }})();
        </script>
        """
    
    @staticmethod
    def show_saved_state_info() -> str:
        """Show what's currently saved in localStorage"""
        return f"""
        <div id="saved-state-info" style="
            background: #e3f2fd;
            border: 2px solid #2196f3;
            border-radius: 12px;
            padding: 12px;
            margin: 10px 0;
            font-family: monospace;
            font-size: 13px;
        "></div>
        <script>
            (function() {{
                const savedChar = localStorage.getItem('{SessionPersistence.STORAGE_KEY}_char');
                const savedTime = localStorage.getItem('{SessionPersistence.STORAGE_KEY}_time');
                const savedHash = localStorage.getItem('{SessionPersistence.STORAGE_KEY}_hash');
                
                const infoEl = document.getElementById('saved-state-info');
                
                if (savedChar && savedChar !== 'none') {{
                    infoEl.innerHTML = `
                        <strong>📌 Last Saved:</strong><br>
                        Character: <strong style="font-size:1.2em">${{savedChar}}</strong><br>
                        Time: ${{savedTime}}<br>
                        Hash: <code>${{savedHash}}</code>
                    `;
                    infoEl.style.display = 'block';
                }} else {{
                    infoEl.innerHTML = '<em>No character saved yet - navigate to one to auto-save</em>';
                    infoEl.style.background = '#fff3e0';
                    infoEl.style.borderColor = '#ff9800';
                }}
            }})();
        </script>
        """
    
    @staticmethod
    def clear_browser_storage() -> str:
        """Clear all saved data"""
        return f"""
        <script>
            localStorage.removeItem('{SessionPersistence.STORAGE_KEY}');
            localStorage.removeItem('{SessionPersistence.STORAGE_KEY}_hash');
            localStorage.removeItem('{SessionPersistence.STORAGE_KEY}_char');
            localStorage.removeItem('{SessionPersistence.STORAGE_KEY}_time');
            console.log('🗑️ [Radix] All saved data cleared');
        </script>
        """


class PersistenceManager:
    """Simplified persistence manager"""
    
    def __init__(self, state_manager):
        self.state = state_manager
    
    def auto_save(self):
        """Auto-save on every render"""
        if self.state.is_onboarding_complete():
            html_content = SessionPersistence.save_to_browser(self.state.state)
            st_html(html_content, height=0)
    
    def try_restore(self):
        """Note: Actual restoration happens via browser refresh"""
        # Just mark that we attempted restoration
        if "_persistence_loaded" not in self.state.state:
            self.state.state["_persistence_loaded"] = True
    
    def add_heartbeat(self):
        """Add heartbeat component"""
        if self.state.is_onboarding_complete():
            html_content = SessionPersistence.get_heartbeat_component()
            st_html(html_content, height=0)
    
    def render_controls(self):
        """Render visible persistence controls"""
        with st.expander("💾 Session Persistence", expanded=False):
            st.caption("Your navigation is **auto-saved** to browser storage. Refresh the page to restore!")
            
            # Show what's currently saved
            info_html = SessionPersistence.show_saved_state_info()
            st_html(info_html, height=120)
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Save Now", use_container_width=True):
                    html_content = SessionPersistence.save_to_browser(self.state.state)
                    st_html(html_content, height=0)
                    st.success("✅ Saved! Check console (F12)", icon="💾")
                    st.rerun()
            
            with col2:
                if st.button("🔄 Test Restore", use_container_width=True):
                    st.info("Close this tab and reopen the app URL")
            
            if st.button("🗑️ Clear Saved State", use_container_width=True):
                html_content = SessionPersistence.clear_browser_storage()
                st_html(html_content, height=0)
                st.success("Cleared! Refresh to confirm.", icon="🗑️")
            
            st.markdown("---")
            st.caption("**How to test:**")
            st.caption("1. Navigate to a character (e.g., 水)")
            st.caption("2. See 'Last Saved' above update")
            st.caption("3. **Close this tab completely**")
            st.caption("4. Open app again - you'll be back at 水!")
            
            # Debug info
            with st.expander("🔍 Current Session State", expanded=False):
                st.json({
                    "selected_char": self.state.get_selected_component() or "none",
                    "history_length": len(self.state.get_history()),
                    "display_mode": self.state.get_display_mode(),
                    "page": self.state.get_current_page(),
                })

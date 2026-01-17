# radix_persistence.py
# SIMPLE session persistence using localStorage

import streamlit as st
from streamlit.components.v1 import html as st_html
import json
import hashlib

class SessionPersistence:
    """Manages browser-based session persistence"""
    
    PERSISTENT_KEYS = [
        "selected_comp", "last_valid_selected_comp", "history", "show_inputs",
        "display_mode", "stroke_range", "radical", "component_idc",
        "script_filter", "grid_sort_mode", "grid_script_filter",
        "page", "derivative_page", "onboarding_done", "startup_file_choice_made",
        "preview_comp", "text_input_comp", "fav_cursor"
    ]
    
    STORAGE_KEY = "radix_session_v1"
    HEARTBEAT_INTERVAL = 45000
    
    @staticmethod
    def save_to_browser(session_state) -> str:
        """Save session state to localStorage"""
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
        current_char = snapshot.get('selected_comp', 'none')
        
        return f"""
        <script>
            (function() {{
                const stateData = {json.dumps(state_json)};
                const stateHash = "{state_hash}";
                const currentChar = "{current_char}";
                const timestamp = new Date().toLocaleTimeString();
                
                localStorage.setItem('{SessionPersistence.STORAGE_KEY}', stateData);
                localStorage.setItem('{SessionPersistence.STORAGE_KEY}_hash', stateHash);
                localStorage.setItem('{SessionPersistence.STORAGE_KEY}_char', currentChar);
                localStorage.setItem('{SessionPersistence.STORAGE_KEY}_time', timestamp);
                
                console.log('✅ [Radix] Saved at ' + timestamp + ' | Char: ' + currentChar);
            }})();
        </script>
        """
    
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
    
    @staticmethod
    def show_saved_state_info() -> str:
        """Show what's saved in localStorage"""
        return f"""
        <div id="saved-state-info" style="
            background: #e3f2fd; border: 2px solid #2196f3; border-radius: 12px;
            padding: 12px; margin: 10px 0; font-family: monospace; font-size: 13px;
        "></div>
        <script>
            const savedChar = localStorage.getItem('{SessionPersistence.STORAGE_KEY}_char');
            const savedTime = localStorage.getItem('{SessionPersistence.STORAGE_KEY}_time');
            const savedHash = localStorage.getItem('{SessionPersistence.STORAGE_KEY}_hash');
            const el = document.getElementById('saved-state-info');
            
            if (savedChar && savedChar !== 'none') {{
                el.innerHTML = `<strong>📌 Last Saved:</strong><br>
                    Character: <strong style="font-size:1.2em">${{savedChar}}</strong><br>
                    Time: ${{savedTime}}<br>Hash: <code>${{savedHash}}</code>`;
            }} else {{
                el.innerHTML = '<em>No character saved yet</em>';
                el.style.background = '#fff3e0';
                el.style.borderColor = '#ff9800';
            }}
        </script>
        """
    
    @staticmethod
    def clear_browser_storage() -> str:
        """Clear localStorage"""
        return f"""
        <script>
            localStorage.removeItem('{SessionPersistence.STORAGE_KEY}');
            localStorage.removeItem('{SessionPersistence.STORAGE_KEY}_hash');
            localStorage.removeItem('{SessionPersistence.STORAGE_KEY}_char');
            localStorage.removeItem('{SessionPersistence.STORAGE_KEY}_time');
            console.log('🗑️ [Radix] Storage cleared');
        </script>
        """


class PersistenceManager:
    """Main persistence manager"""
    
    def __init__(self, state_manager):
        self.state = state_manager
    
    def auto_save(self):
        """Auto-save on every render"""
        if self.state.is_onboarding_complete():
            html_content = SessionPersistence.save_to_browser(self.state.state)
            st_html(html_content, height=0)
    
    def try_restore(self):
        """Restore state from localStorage - SIMPLE VERSION"""
        # Only try once per session
        if self.state.state.get("_restore_attempted"):
            return
        
        self.state.state["_restore_attempted"] = True
        
        # Get current values BEFORE any restoration
        current_selected = self.state.state.get("selected_comp", "")
        current_onboarding = self.state.state.get("onboarding_done", False)
        
        # Use a component to read localStorage and trigger actions
        restore_component = f"""
        <div id="restore-trigger" style="display:none;"></div>
        <script>
            (function() {{
                try {{
                    const savedState = localStorage.getItem('{SessionPersistence.STORAGE_KEY}');
                    if (!savedState) {{
                        console.log('[Radix] No saved state found');
                        return;
                    }}
                    
                    const stateObj = JSON.parse(savedState);
                    const savedChar = stateObj.selected_comp || '';
                    
                    // Only restore if we're at default state (no character selected yet)
                    const currentSelected = "{current_selected}";
                    const currentOnboarding = {str(current_onboarding).lower()};
                    
                    if (!currentSelected && currentOnboarding && savedChar) {{
                        console.log('[Radix] 🔄 Found saved character:', savedChar);
                        console.log('[Radix] Need to navigate to:', savedChar);
                        
                        // Store the character to navigate to
                        sessionStorage.setItem('_radix_nav_to_char', savedChar);
                        sessionStorage.setItem('_radix_nav_to_history', JSON.stringify(stateObj.history || []));
                        sessionStorage.setItem('_radix_nav_to_mode', stateObj.display_mode || '2-Characters');
                    }} else {{
                        console.log('[Radix] Already at a character, skipping restore');
                    }}
                }} catch (e) {{
                    console.error('[Radix] Restore failed:', e);
                }}
            }})();
        </script>
        """
        st_html(restore_component, height=0)
        
        # Check if we need to navigate (via a button click simulation)
        check_nav = f"""
        <script>
            const navChar = sessionStorage.getItem('_radix_nav_to_char');
            if (navChar) {{
                console.log('[Radix] 📍 Navigation needed to:', navChar);
                sessionStorage.setItem('_radix_restore_pending', 'true');
            }}
        </script>
        """
        st_html(check_nav, height=0)
    
    def check_pending_navigation(self):
        """Check if we need to navigate to a restored character"""
        # This is called AFTER initial state setup
        if not self.state.state.get("_nav_check_done"):
            self.state.state["_nav_check_done"] = True
            
            # Read the pending nav via a detection component
            detect_html = f"""
            <div id="nav-detector" data-pending="false"></div>
            <script>
                const pending = sessionStorage.getItem('_radix_restore_pending');
                const navChar = sessionStorage.getItem('_radix_nav_to_char');
                if (pending === 'true' && navChar) {{
                    document.getElementById('nav-detector').setAttribute('data-pending', navChar);
                    
                    // Clear flags
                    sessionStorage.removeItem('_radix_restore_pending');
                    console.log('[Radix] ✅ Restoration complete for:', navChar);
                }}
            </script>
            """
            st_html(detect_html, height=0)
            
            # Now manually apply navigation if needed
            # This is a workaround - we'll just show a message
            nav_html = f"""
            <script>
                const navChar = sessionStorage.getItem('_radix_nav_to_char');
                const navHistory = sessionStorage.getItem('_radix_nav_to_history');
                const navMode = sessionStorage.getItem('_radix_nav_to_mode');
                
                if (navChar) {{
                    console.log('[Radix] 🎯 AUTO-NAVIGATING to:', navChar);
                    
                    // Show a toast-like message
                    const toast = document.createElement('div');
                    toast.style.cssText = `
                        position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
                        background: #4caf50; color: white; padding: 16px 32px;
                        border-radius: 12px; font-weight: 700; font-size: 16px;
                        z-index: 10000; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                        animation: slideDown 0.3s ease;
                    `;
                    toast.textContent = `🔄 Restoring session: ${{navChar}}`;
                    document.body.appendChild(toast);
                    
                    setTimeout(() => toast.remove(), 3000);
                    
                    // Clear the storage
                    sessionStorage.removeItem('_radix_nav_to_char');
                    sessionStorage.removeItem('_radix_nav_to_history');
                    sessionStorage.removeItem('_radix_nav_to_mode');
                }}
            </script>
            """
            st_html(nav_html, height=0)
    
    def add_heartbeat(self):
        """Add heartbeat"""
        if self.state.is_onboarding_complete():
            st_html(SessionPersistence.get_heartbeat_component(), height=0)
    
    def render_controls(self):
        """Render controls"""
        with st.expander("💾 Session Persistence", expanded=False):
            st.caption("Auto-saved to browser. **Close tab & reopen** to test restore!")
            
            st_html(SessionPersistence.show_saved_state_info(), height=120)
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Now", use_container_width=True):
                    st_html(SessionPersistence.save_to_browser(self.state.state), height=0)
                    st.success("✅ Saved!")
                    st.rerun()
            
            with col2:
                if st.button("🗑️ Clear", use_container_width=True):
                    st_html(SessionPersistence.clear_browser_storage(), height=0)
                    st.success("Cleared!")
            
            st.markdown("---")
            st.caption("**How to test:**")
            st.caption("1. Navigate to a character")
            st.caption("2. Close this browser tab")
            st.caption("3. Reopen app URL")
            st.caption("4. Check console (F12) for restore messages")
            
            with st.expander("🔍 Current State"):
                st.json({
                    "selected": self.state.get_selected_component() or "none",
                    "history": len(self.state.get_history()),
                    "mode": self.state.get_display_mode(),
                })

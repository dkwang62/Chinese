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
        """Restore state from localStorage - DIRECT APPLICATION"""
        # Only try once per session
        if self.state.state.get("_restore_attempted"):
            return
        
        self.state.state["_restore_attempted"] = True
        
        # Check if we're starting fresh (no character selected, onboarding done)
        current_selected = self.state.state.get("selected_comp", "")
        onboarding_done = self.state.state.get("onboarding_done", False)
        show_inputs = self.state.state.get("show_inputs", True)
        
        # Only restore if we're at the default start state
        if current_selected or not onboarding_done or not show_inputs:
            # Already navigated somewhere, don't restore
            return
        
        # Inject a component that reads localStorage and stores in sessionStorage
        read_component = f"""
        <script>
            (function() {{
                try {{
                    const savedState = localStorage.getItem('{SessionPersistence.STORAGE_KEY}');
                    if (!savedState) {{
                        console.log('[Radix] No saved state found');
                        return;
                    }}
                    
                    const stateObj = JSON.parse(savedState);
                    console.log('[Radix] 📦 Loaded state:', stateObj);
                    
                    // Store each key in sessionStorage so Python can read it
                    for (const [key, value] of Object.entries(stateObj)) {{
                        sessionStorage.setItem('_radix_restore_' + key, JSON.stringify(value));
                    }}
                    
                    sessionStorage.setItem('_radix_restore_ready', 'true');
                    console.log('[Radix] ✅ State ready for restoration');
                    
                }} catch (e) {{
                    console.error('[Radix] Failed to load state:', e);
                }}
            }})();
        </script>
        """
        st_html(read_component, height=0)
        
        # Now check if restore is ready and apply it
        check_component = f"""
        <div id="restore-status" style="display:none;"></div>
        <script>
            const ready = sessionStorage.getItem('_radix_restore_ready');
            if (ready === 'true') {{
                document.getElementById('restore-status').setAttribute('data-ready', 'true');
                const char = JSON.parse(sessionStorage.getItem('_radix_restore_selected_comp') || '""');
                if (char) {{
                    document.getElementById('restore-status').setAttribute('data-char', char);
                }}
            }}
        </script>
        """
        st_html(check_component, height=0)
        
        # Since we can't read DOM attributes, we'll use a different approach:
        # Just apply the restoration directly if it's the first load
        
        # Check if this looks like a fresh page load (not a rerun)
        if '_radix_first_load' not in self.state.state:
            self.state.state['_radix_first_load'] = False
            
            # This IS the first load - try to restore
            # We'll trigger a rerun with query params
            trigger_restore = f"""
            <script>
                (function() {{
                    const ready = sessionStorage.getItem('_radix_restore_ready');
                    if (ready === 'true') {{
                        const char = JSON.parse(sessionStorage.getItem('_radix_restore_selected_comp') || '""');
                        
                        if (char && char !== 'none' && char !== '') {{
                            console.log('[Radix] 🎯 Triggering restore to:', char);
                            
                            // Add to URL to trigger navigation
                            const params = new URLSearchParams(window.location.search);
                            params.set('_restore_to', char);
                            const newUrl = window.location.pathname + '?' + params.toString();
                            
                            // Navigate to new URL (this will reload Streamlit)
                            window.location.href = newUrl;
                        }}
                        
                        // Clear the flag so we don't loop
                        sessionStorage.removeItem('_radix_restore_ready');
                    }}
                }})();
            </script>
            """
            st_html(trigger_restore, height=0)
        
        # Check if we have a restore target in query params
        if '_restore_to' in st.query_params:
            char_to_restore = st.query_params['_restore_to']
            
            # Clear the param immediately
            new_params = {k: v for k, v in st.query_params.items() if k != '_restore_to'}
            st.query_params.clear()
            for k, v in new_params.items():
                st.query_params[k] = v
            
            # Apply the restoration - use the proper navigation method
            if char_to_restore and char_to_restore != 'none':
                # Use the state manager's enter_character_view method
                self.state.enter_character_view(char_to_restore)
                
                st.toast(f"🔄 Restored session: {char_to_restore}", icon="✅")
                
                # Force a rerun to show the character view
                st.rerun()
    
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

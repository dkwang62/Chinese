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
        
        # Debug: log what we're actually saving
        show_inputs = snapshot.get('show_inputs', True)
        
        return f"""
        <script>
            (function() {{
                const stateData = {json.dumps(state_json)};
                const stateHash = "{state_hash}";
                const currentChar = "{current_char}";
                const showInputs = {str(show_inputs).lower()};
                const timestamp = new Date().toLocaleTimeString();
                
                // Parse and log the actual state being saved
                const parsedState = JSON.parse(stateData);
                console.log('[Radix] 💾 Saving state:');
                console.log('  - Character:', currentChar);
                console.log('  - Show inputs:', showInputs);
                console.log('  - Full state:', parsedState);
                
                localStorage.setItem('{SessionPersistence.STORAGE_KEY}', stateData);
                localStorage.setItem('{SessionPersistence.STORAGE_KEY}_hash', stateHash);
                localStorage.setItem('{SessionPersistence.STORAGE_KEY}_char', currentChar);
                localStorage.setItem('{SessionPersistence.STORAGE_KEY}_time', timestamp);
                
                console.log('✅ [Radix] Saved at ' + timestamp);
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
        """Restore state from localStorage.

        Strategy:
        - JS reads localStorage and redirects with a query param.
        - Python validates via the same single-character validation used by Search,
          then navigates via enter_character_view.

        This works even when the user is still on the startup/onboarding screens.
        """

        # --- 1) If a restore request came in via query params, apply it immediately ---
        restore_char = None
        if '_restore_search' in st.query_params:
            restore_char = st.query_params.get('_restore_search', '')
        elif '_restore_to' in st.query_params:
            # Back-compat: older param name
            restore_char = st.query_params.get('_restore_to', '')

        if restore_char:
            # Clear params immediately to avoid rerun loops
            st.query_params.clear()

            from radix_state import InputValidator
            validated = InputValidator.validate_character_input(restore_char)

            if validated:
                # Bypass startup + onboarding layers
                self.state.complete_startup()
                self.state.complete_onboarding()

                # Navigate using the same logic as Search
                self.state.enter_character_view(validated)
                st.toast(f"🔄 Restored session: {validated}", icon="✅")
                self.state.state["_restore_attempted"] = True
                st.rerun()
            else:
                # Mark attempted so we don't keep trying a bad value
                self.state.state["_restore_attempted"] = True
            return

        # --- 2) Otherwise, inject a one-time JS trigger to pull localStorage and redirect ---
        if self.state.state.get("_restore_attempted"):
            return
        self.state.state["_restore_attempted"] = True

        # If the app already has a selected component, don't override it
        if self.state.state.get("selected_comp", ""):
            return

        trigger_restore = f"""
        <script>
            (function() {{
                try {{
                    const savedState = localStorage.getItem('{SessionPersistence.STORAGE_KEY}');
                    if (!savedState) {{
                        console.log('[Radix] No saved state to restore');
                        return;
                    }}

                    const stateObj = JSON.parse(savedState);
                    // Prefer selected_comp, then last_valid_selected_comp
                    const savedChar = (stateObj.selected_comp || stateObj.last_valid_selected_comp || '').trim();

                    console.log('[Radix] Found saved state:', stateObj);
                    console.log('[Radix] Candidate restore char:', savedChar);

                    // Only attempt redirect if we have a plausible single character
                    if (savedChar && savedChar !== 'none' && savedChar.length === 1) {{
                        const params = new URLSearchParams(window.location.search);
                        params.set('_restore_search', savedChar);

                        const newUrl = window.location.pathname + '?' + params.toString();
                        console.log('[Radix] Redirecting to:', newUrl);
                        window.location.href = newUrl;
                    }} else {{
                        console.log('[Radix] No valid single-character restore target');
                    }}
                }} catch (e) {{
                    console.error('[Radix] Restore trigger failed:', e);
                }}
            }})();
        </script>
        """

        st_html(trigger_restore, height=0)
    
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
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("💾 Save Now", use_container_width=True):
                    st_html(SessionPersistence.save_to_browser(self.state.state), height=0)
                    st.success("✅ Saved!")
                    st.rerun()
            
            with col2:
                if st.button("🔄 Test Restore", use_container_width=True):
                    # Read from localStorage and navigate
                    test_html = f"""
                    <script>
                        const savedState = localStorage.getItem('{SessionPersistence.STORAGE_KEY}');
                        console.log('[Radix] Test Restore clicked');
                        console.log('[Radix] Raw savedState:', savedState);
                        
                        if (savedState) {{
                            try {{
                                const stateObj = JSON.parse(savedState);
                                console.log('[Radix] Parsed state:', stateObj);
                                
                                const char = stateObj.selected_comp || '';
                                const showInputs = stateObj.show_inputs;
                                
                                console.log('[Radix] Character from state:', char);
                                console.log('[Radix] Show inputs:', showInputs);
                                
                                if (char && char !== 'none' && char !== '') {{
                                    console.log('[Radix] ✅ Valid character found, navigating to:', char);
                                    const params = new URLSearchParams(window.location.search);
                                    params.set('_restore_to', char);
                                    window.location.href = window.location.pathname + '?' + params.toString();
                                }} else {{
                                    console.log('[Radix] ❌ No valid character to restore');
                                    alert('No character saved to restore (found: "' + char + '")');
                                }}
                            }} catch (e) {{
                                console.error('[Radix] Failed to parse state:', e);
                                alert('Failed to parse saved state: ' + e.message);
                            }}
                        }} else {{
                            console.log('[Radix] ❌ No saved state in localStorage');
                            alert('No saved state found in browser storage');
                        }}
                    </script>
                    """
                    st_html(test_html, height=0)
            
            with col3:
                if st.button("🗑️ Clear", use_container_width=True):
                    st_html(SessionPersistence.clear_browser_storage(), height=0)
                    st.success("Cleared!")
            
            st.markdown("---")
            st.caption("**Quick test:** Click '🔄 Test Restore' to manually trigger restoration")
            st.caption("**Full test:** Close tab → Reopen app URL")
            st.caption("**Debug:** Open console (F12) for restore messages")
            
            with st.expander("🔍 Current State"):
                st.json({
                    "selected": self.state.get_selected_component() or "none",
                    "history": len(self.state.get_history()),
                    "mode": self.state.get_display_mode(),
                })

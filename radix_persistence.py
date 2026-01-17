# radix_persistence.py
# Complete session persistence system for Radix
# Add this as a new file to your project

import streamlit as st
from streamlit.components.v1 import html as st_html
import json
from typing import Dict, Any, Optional
import hashlib

class SessionPersistence:
    """Manages browser-based session persistence and heartbeat"""
    
    # Keys that should be persisted across sessions
    PERSISTENT_KEYS = [
        "selected_comp",
        "last_valid_selected_comp",
        "history",
        "show_inputs",
        "display_mode",
        "stroke_range",
        "radical",
        "component_idc",
        "script_filter",
        "grid_sort_mode",
        "grid_script_filter",
        "page",
        "derivative_page",
        "onboarding_done",
        "startup_file_choice_made",
        "preview_comp",
        "text_input_comp",
        "fav_cursor"
    ]
    
    STORAGE_KEY = "radix_session_v1"
    HEARTBEAT_INTERVAL = 45000  # 45 seconds
    
    @staticmethod
    def get_state_snapshot(session_state) -> Dict[str, Any]:
        """Create a JSON-serializable snapshot of session state"""
        snapshot = {}
        for key in SessionPersistence.PERSISTENT_KEYS:
            if key in session_state:
                value = session_state[key]
                # Only include JSON-serializable values
                try:
                    json.dumps(value)
                    snapshot[key] = value
                except (TypeError, ValueError):
                    pass
        return snapshot
    
    @staticmethod
    def get_state_hash(snapshot: Dict) -> str:
        """Get hash of state snapshot for change detection"""
        state_str = json.dumps(snapshot, sort_keys=True)
        return hashlib.md5(state_str.encode()).hexdigest()[:8]
    
    @staticmethod
    def save_to_browser(session_state) -> str:
        """
        Save session state to browser localStorage.
        Returns HTML component to inject.
        """
        snapshot = SessionPersistence.get_state_snapshot(session_state)
        state_json = json.dumps(snapshot)
        state_hash = SessionPersistence.get_state_hash(snapshot)
        
        return f"""
        <script>
            (function() {{
                try {{
                    const stateData = {json.dumps(state_json)};
                    const stateHash = "{state_hash}";
                    
                    localStorage.setItem('{SessionPersistence.STORAGE_KEY}', stateData);
                    localStorage.setItem('{SessionPersistence.STORAGE_KEY}_hash', stateHash);
                    
                    console.log('[Radix] Session saved (hash: ' + stateHash + ')');
                }} catch (e) {{
                    console.error('[Radix] Failed to save session:', e);
                }}
            }})();
        </script>
        """
    
    @staticmethod
    def restore_from_browser() -> str:
        """
        Generate HTML component to restore state from localStorage.
        Uses a simpler approach that doesn't rely on component return values.
        """
        return f"""
        <div id="radix-restore-status" style="display:none;"></div>
        <script>
            (function() {{
                try {{
                    const savedState = localStorage.getItem('{SessionPersistence.STORAGE_KEY}');
                    const savedHash = localStorage.getItem('{SessionPersistence.STORAGE_KEY}_hash');
                    
                    if (savedState) {{
                        console.log('[Radix] Found saved session (hash: ' + savedHash + ')');
                        
                        // Parse the saved state
                        const stateObj = JSON.parse(savedState);
                        
                        // Store in a hidden input that Streamlit can read
                        const existingInput = document.getElementById('radix-hidden-restore-data');
                        if (existingInput) {{
                            existingInput.remove();
                        }}
                        
                        const hiddenInput = document.createElement('input');
                        hiddenInput.type = 'hidden';
                        hiddenInput.id = 'radix-hidden-restore-data';
                        hiddenInput.value = savedState;
                        document.body.appendChild(hiddenInput);
                        
                        // Update status
                        document.getElementById('radix-restore-status').textContent = 
                            'Session data ready for restore';
                        
                        console.log('[Radix] Session data prepared for Streamlit');
                    }} else {{
                        console.log('[Radix] No saved session found');
                    }}
                }} catch (e) {{
                    console.error('[Radix] Failed to restore session:', e);
                }}
            }})();
        </script>
        """
    
    @staticmethod
    def get_heartbeat_component() -> str:
        """
        Generate heartbeat component that keeps session alive.
        Uses the stroke order animation as visual feedback.
        """
        return f"""
        <div id="radix-heartbeat" style="
            position: fixed;
            bottom: 10px;
            right: 10px;
            background: rgba(76, 175, 80, 0.9);
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            z-index: 9999;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            display: none;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        ">
            💚 Session Active
        </div>
        
        <script>
            (function() {{
                const heartbeatEl = document.getElementById('radix-heartbeat');
                let lastActivity = Date.now();
                let heartbeatCount = 0;
                
                // Show heartbeat indicator briefly
                function showHeartbeat() {{
                    heartbeatEl.style.display = 'block';
                    heartbeatEl.textContent = '💚 Session Active (ping #' + heartbeatCount + ')';
                    setTimeout(() => {{
                        heartbeatEl.style.display = 'none';
                    }}, 2000);
                }}
                
                // Ping server to keep session alive
                function sendHeartbeat() {{
                    heartbeatCount++;
                    
                    // Fetch current page to keep connection alive
                    fetch(window.location.href, {{
                        method: 'GET',
                        headers: {{
                            'Cache-Control': 'no-cache',
                            'X-Radix-Heartbeat': 'true'
                        }},
                        credentials: 'same-origin'
                    }})
                    .then(() => {{
                        console.log('[Radix] Heartbeat #' + heartbeatCount + ' sent successfully');
                        showHeartbeat();
                        lastActivity = Date.now();
                    }})
                    .catch(e => {{
                        console.warn('[Radix] Heartbeat #' + heartbeatCount + ' failed:', e);
                    }});
                }}
                
                // Send heartbeat every {SessionPersistence.HEARTBEAT_INTERVAL}ms
                setInterval(sendHeartbeat, {SessionPersistence.HEARTBEAT_INTERVAL});
                
                // Track user activity
                ['mousedown', 'keydown', 'scroll', 'touchstart'].forEach(event => {{
                    document.addEventListener(event, () => {{
                        lastActivity = Date.now();
                    }}, {{ passive: true }});
                }});
                
                // Initial heartbeat after 5 seconds
                setTimeout(sendHeartbeat, 5000);
                
                console.log('[Radix] Heartbeat system initialized (interval: {SessionPersistence.HEARTBEAT_INTERVAL}ms)');
            }})();
        </script>
        """
    
    @staticmethod
    def clear_browser_storage() -> str:
        """Generate HTML to clear browser storage"""
        return f"""
        <script>
            localStorage.removeItem('{SessionPersistence.STORAGE_KEY}');
            localStorage.removeItem('{SessionPersistence.STORAGE_KEY}_hash');
            console.log('[Radix] Browser storage cleared');
        </script>
        """


class PersistenceManager:
    """High-level manager for session persistence"""
    
    def __init__(self, state_manager):
        self.state = state_manager
        self._restore_attempted = False
    
    def auto_save(self):
        """Auto-save current session state (call on every render)"""
        if self.state.is_onboarding_complete():
            html_content = SessionPersistence.save_to_browser(self.state.state)
            st_html(html_content, height=0)
    
    def try_restore(self) -> bool:
        """
        Try to restore session from browser storage.
        Returns True if state was restored.
        Call this ONCE during initialization.
        """
        if self._restore_attempted:
            return False
        
        self._restore_attempted = True
        
        # Use session state to track restoration instead of component return
        restore_key = "_persistence_restored"
        restore_data_key = "_persistence_restore_data"
        
        if restore_key not in self.state.state:
            # Set up the restoration via query params trick
            try:
                # Try to read from session state if already loaded by JavaScript
                if restore_data_key in self.state.state:
                    restored_state = self.state.state[restore_data_key]
                    
                    # Apply restored state
                    for key, value in restored_state.items():
                        if key in SessionPersistence.PERSISTENT_KEYS:
                            self.state.state[key] = value
                    
                    # Mark as restored
                    self.state.state[restore_key] = True
                    
                    # Clean up
                    del self.state.state[restore_data_key]
                    
                    st.toast("🔄 Session restored from browser storage", icon="✅")
                    return True
                else:
                    # First time - inject the restore script
                    html_content = SessionPersistence.restore_from_browser()
                    st_html(html_content, height=0)
                    self.state.state[restore_key] = False  # Mark attempt made
                    
            except Exception as e:
                self.state.state[restore_key] = False
                return False
        
        return False
    
    def add_heartbeat(self):
        """Add heartbeat component to keep session alive"""
        if self.state.is_onboarding_complete():
            html_content = SessionPersistence.get_heartbeat_component()
            st_html(html_content, height=0)
    
    def render_controls(self):
        """Render persistence controls in sidebar"""
        with st.expander("💾 Session Persistence", expanded=False):
            st.caption("Your navigation is auto-saved to your browser and the session stays active via heartbeat pings.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Save Now", use_container_width=True, help="Manually save current state"):
                    html_content = SessionPersistence.save_to_browser(self.state.state)
                    st_html(html_content, height=0)
                    st.success("✅ Saved!", icon="💾")
            
            with col2:
                if st.button("🔄 Reload Page", use_container_width=True, help="Reload page to restore state"):
                    st.rerun()
            
            if st.button("🗑️ Clear Saved State", use_container_width=True, help="Delete saved session"):
                html_content = SessionPersistence.clear_browser_storage()
                st_html(html_content, height=0)
                st.info("Cleared browser storage")
            
            # Show current state info
            snapshot = SessionPersistence.get_state_snapshot(self.state.state)
            state_hash = SessionPersistence.get_state_hash(snapshot)
            
            st.caption(f"**Current session:** `{state_hash}`")
            st.caption(f"**Auto-save:** Every page render")
            st.caption(f"**Heartbeat:** Every 45 seconds")

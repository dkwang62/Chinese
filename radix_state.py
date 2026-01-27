# radix_state.py - CLEANED VERSION
# State management using templates and utilities

import streamlit as st
import json
from typing import Any, Dict, List, Optional, Callable
from radix_core import normalize_single_hanzi, resolve_to_known_variant
import streamlit.components.v1 as components

# Import utilities
from radix_utils import deduplicate_list


# ==================== CONSTANTS ====================

PAGE_CONFIG = {"layout": "wide", "page_title": "Radix", "page_icon": "🈑"}
PROFILE_SCHEMA_VERSION = 1
PROFILE_FILENAME = "radix_user_data.json"

PAGE_SIZE = 120
GRID_COLUMNS = 10
MAX_DERIVATIVES_DISPLAY = 120

DISPLAY_MODES = ["Single Character", "2-Characters", "3-Characters", "4-Characters"]
SCRIPT_FILTERS = ["Any", "Simplified", "Traditional"]

DEFAULT_STATE = {
    "startup_file_choice_made": False,
    "onboarding_done": False,
    "selected_comp": "",
    "stroke_range": (3, 8),
    "radical": "none",
    "component_idc": "none",
    "display_mode": "2-Characters",
    "text_input_comp": "",
    "page": 1,
    "text_input_warning": None,
    "show_inputs": True,
    "last_valid_selected_comp": "",
    "preview_comp": None,
    "stroke_view_active": False,
    "stroke_view_char": "",
    "script_filter": "Any",
    "favourites_list": [],
    "fav_cursor": 0,
    "prompt_config": None,
    "prompt_ui": {"default_selected_task_ids": []},
    "prompt_selected_task_ids": [],
    "history": [],
    "definition_search_mode": False,
    "definition_search_query": "",
    "definition_search_results": None,
    "grid_sort_mode": "usage",
    "grid_script_filter": "Any",
    "derivative_page": 0,
}

# State update templates - consolidates duplicate patterns
STATE_TEMPLATES = {
    'character_view': {
        'script_filter': 'Any',
        'show_inputs': False,
        'preview_comp': None,
        'stroke_view_active': False,
        'stroke_view_char': '',
        'display_mode': '2-Characters',
        'definition_search_mode': False,
        'definition_search_results': None,
        'derivative_page': 0,
        'text_input_warning': None,
    },
    'inputs_view': {
        'show_inputs': True,
        'selected_comp': '',
        'last_valid_selected_comp': '',
        'preview_comp': None,
        'stroke_view_active': False,
        'stroke_view_char': '',
        'definition_search_mode': False,
        'definition_search_results': None,
    },
    'stroke_view': {
        'stroke_view_active': True,
        'show_inputs': False,
        'definition_search_mode': False,
    },
}

# ==================== INPUT VALIDATION ====================

class InputValidator:
    """Input validation and normalization."""
    
    @staticmethod
    def validate_character_input(raw: str, error_callback: Optional[Callable] = None) -> Optional[str]:
        """Validate single character input."""
        v = normalize_single_hanzi(raw)
        if not v:
            if error_callback:
                error_callback("One character only")
            return None
        
        resolved = resolve_to_known_variant(v)
        if not resolved:
            if error_callback:
                error_callback("Not found")
            return None
        
        return resolved
    
    @staticmethod
    def validate_definition_search(query: str) -> tuple[bool, Optional[str]]:
        """Validate definition search query."""
        query = query.strip()
        if not query or len(query) < 2:
            return False, "Please enter at least 2 characters to search."
        return True, None

# ==================== STATE MANAGER ====================

class StateManager:
    """Centralized session state management with templates."""
    
    def __init__(self):
        self.state = st.session_state
    
    def initialize(self):
        """Initialize all default state values."""
        for key, value in DEFAULT_STATE.items():
            if key not in self.state:
                self.state[key] = value
    
    # --- Getters ---
    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)
    
    def get_selected_component(self) -> str:
        return self.state.get("selected_comp", "")
    
    def get_preview_component(self) -> Optional[str]:
        return self.state.get("preview_comp")
    
    def get_display_mode(self) -> str:
        return self.state.get("display_mode", "2-Characters")
    
    def get_favourites(self) -> List[str]:
        return self.state.get("favourites_list", [])
    
    def get_history(self) -> List[str]:
        return self.state.get("history", [])
    
    def get_stroke_range(self) -> tuple:
        return self.state.get("stroke_range", (3, 8))
    
    def get_script_filter(self) -> str:
        return self.state.get("script_filter", "Any")
    
    def get_grid_sort_mode(self) -> str:
        return self.state.get("grid_sort_mode", "usage")
    
    def get_current_page(self) -> int:
        return self.state.get("page", 1)
    
    # --- Setters ---
    def set(self, key: str, value: Any):
        self.state[key] = value
    
    def update(self, *args, **kwargs):
        self.state.update(*args, **kwargs)
    
    def pop(self, key: str, default: Any = None) -> Any:
        return self.state.pop(key, default)
    
    # --- Boolean Checks ---
    def is_startup_complete(self) -> bool:
        return self.state.get("startup_file_choice_made", False)
    
    def is_onboarding_complete(self) -> bool:
        return self.state.get("onboarding_done", False)
    
    def is_showing_inputs(self) -> bool:
        return self.state.get("show_inputs", True)
    
    def is_stroke_view_active(self) -> bool:
        return self.state.get("stroke_view_active", False)
    
    def is_definition_search_active(self) -> bool:
        return self.state.get("definition_search_mode", False)

    # --- Navigation Actions (Using Templates) ---
    def enter_character_view(self, char: str):
        """Enter character view with given character."""
        if char:
            st.query_params["c"] = char

        # Use template and override with character-specific values
        template = STATE_TEMPLATES['character_view'].copy()
        template.update({
            'selected_comp': char,
            'last_valid_selected_comp': char,
            'text_input_comp': char,
        })
        self.update(**template)
    
    def go_back(self):
        """Navigate back in history."""
        history = self.get_history()
        if history:
            prev = history.pop()
            self.set("history", history)
            self.enter_character_view(prev)
        else:
            self.show_inputs()
    
    def show_inputs(self):
        """Show input grid."""
        # Use template
        self.update(**STATE_TEMPLATES['inputs_view'])
        st.query_params.clear()
    
    def enter_stroke_view(self, char: str):
        """Enter stroke view for character."""
        if char:
            # Use template and override
            template = STATE_TEMPLATES['stroke_view'].copy()
            template.update({
                'stroke_view_char': char,
                'selected_comp': char,
                'last_valid_selected_comp': char,
            })
            self.update(**template)
            st.query_params["c"] = char
    
    def exit_stroke_view(self):
        """Exit stroke view."""
        self.update(stroke_view_active=False, stroke_view_char="")
    
    def complete_onboarding(self):
        self.set("onboarding_done", True)
    
    def complete_startup(self):
        self.set("startup_file_choice_made", True)
    
    # --- List Operations ---
    def add_to_favourites(self, char: str):
        """Add character to favourites list."""
        favs = self.get_favourites()
        if char not in favs:
            favs.append(char)
            self.set("favourites_list", favs)
    
    def remove_from_favourites(self, char: str):
        """Remove character from favourites."""
        favs = self.get_favourites()
        if char in favs:
            favs.remove(char)
            self.set("favourites_list", favs)
    
    def toggle_favourite(self, char: str):
        """Toggle favourite status."""
        if char in self.get_favourites():
            self.remove_from_favourites(char)
        else:
            self.add_to_favourites(char)
    
    def clear_widgets_by_prefix(self, prefixes: List[str]):
        """Clear widget states by prefix - consolidates duplicate loops."""
        keys_to_clear = [
            k for k in list(self.state.keys())
            if any(k.startswith(prefix) or k == prefix for prefix in prefixes)
        ]
        for k in keys_to_clear:
            self.state.pop(k, None)
    
    def clear_derived_widget_state(self):
        """Clear all derived UI widget states."""
        prefixes = [
            "fav_bulk_editor",
            "pt_title_",
            "pt_tpl_",
            "prompt_task_cb_",
            "prompt_selected_task_ids",
            "prompt_default_sel_editor",
            "fav_chk_",
        ]
        self.clear_widgets_by_prefix(prefixes)

    def process_search_and_clear(self, raw_input: str, widget_key: str, error_callback=None):
        """Process search, clear widget, and handle onboarding completion."""
        validated = InputValidator.validate_character_input(raw_input, error_callback)
        if validated:
            self.state[widget_key] = ""
            self.set("onboarding_done", True)
            self.enter_character_view(validated)
            return True
        return False

# ==================== CONFIG MANAGER ====================

class ConfigManager:
    """Configuration and profile management."""
    
    def __init__(self, state_manager: StateManager):
        self.state = state_manager
    
    def build_profile_dict(self) -> Dict:
        """Build complete profile dictionary."""
        return {
            "schema_version": PROFILE_SCHEMA_VERSION,
            "favourites_list": self.state.get_favourites(),
            "prompt_config": self.state.get("prompt_config", {}),
            "prompt_ui": self.state.get("prompt_ui", {}),
        }
    
    def export_profile_str(self) -> str:
        """Export profile as JSON string."""
        return json.dumps(self.build_profile_dict(), ensure_ascii=False, indent=2)
    
    def import_profile_dict(self, data: Dict):
        """Import profile from dictionary."""
        if not isinstance(data, dict):
            raise ValueError("Uploaded JSON must be an object.")
        if data.get("schema_version") != PROFILE_SCHEMA_VERSION:
            raise ValueError("Unsupported schema_version.")
        
        self.state.set("favourites_list", data.get("favourites_list", []))
        self.state.set("fav_cursor", 0)
        self.state.set("prompt_config", data.get("prompt_config", {}))
        
        prompt_ui = data.get("prompt_ui", {})
        self.state.set("prompt_ui", prompt_ui if isinstance(prompt_ui, dict) else {})
    
    def import_profile_bytes(self, file_bytes: bytes):
        """Import profile from file bytes."""
        try:
            obj = json.loads(file_bytes.decode("utf-8"))
            self.state.clear_derived_widget_state()
            self.import_profile_dict(obj)
            
            self.state.update({
                "_upload_applied": True,
                "_manual_config_active": True,
                "_post_apply_rerun": True
            })
            
            self.state.pop("_upload_error", None)
            self.normalize_prompt_state()
        except Exception as e:
            self.state.set("_upload_error", f"Invalid JSON: {e}")
            self.state.set("_upload_applied", False)
    
    def load_server_data(self):
        """Load server-side user data if available."""
        if self.state.get("server_data_loaded"):
            return
        
        self.state.set("server_data_loaded", True)
        self.state.set("server_data_available", False)
        
        if self.state.get("_manual_config_active"):
            return
        
        try:
            with open(PROFILE_FILENAME, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict) and obj.get("schema_version") == PROFILE_SCHEMA_VERSION:
                self.state.set("server_data", obj)
                self.state.set("server_data_available", True)
        except FileNotFoundError:
            pass
        except Exception as e:
            st.error(f"Error loading {PROFILE_FILENAME}: {e}")
    
    def get_default_prompt_config(self) -> Dict:
        """Get default prompt configuration."""
        return {
            "version": 1,
            "preamble": "You are a bilingual Chinese dictionary editor and teacher.\n\nExplain a single Chinese character in depth for language learners.\n\n⸻\n\n",
            "tasks": [
                {"id": "task1", "title": "Task 1 – Character Analysis", "template": "Task 1 — Character Analysis\n\n⸻\n\n"},
                {"id": "task2", "title": "Task 2 – Example Sentences", "template": "Task 2 — Example Sentences\n\n⸻\n\n"},
                {"id": "task3", "title": "Task 3 – Conceptual Contrast", "template": "Task 3 — Conceptual Contrast\n\n⸻\n\n"},
            ],
            "epilogue": "Hanzi: {char}\n- English definition: {def_en}\n",
        }
    
    def normalize_prompt_state(self):
        """Ensure prompt config and UI state are internally consistent."""
        cfg = self.state.get("prompt_config") or {}
        tasks = cfg.get("tasks", []) or []
        
        # Clean tasks - use utility for deduplication
        cleaned_tasks = []
        seen_ids = set()
        for t in tasks:
            if isinstance(t, dict) and t.get("id") and t["id"] not in seen_ids:
                seen_ids.add(t["id"])
                cleaned_tasks.append(t)
        
        cfg["tasks"] = cleaned_tasks
        self.state.set("prompt_config", cfg)
        
        # Update UI state
        all_task_ids = [t["id"] for t in cleaned_tasks]
        pui = self.state.get("prompt_ui") or {}
        default_ids = pui.get("default_selected_task_ids", [])
        pui["default_selected_task_ids"] = [t for t in default_ids if t in all_task_ids] or list(all_task_ids)
        self.state.set("prompt_ui", pui)
        
        cur_sel = self.state.get("prompt_selected_task_ids") or []
        self.state.set("prompt_selected_task_ids", [t for t in cur_sel if t in all_task_ids] or list(pui["default_selected_task_ids"]))
        
        for tid in all_task_ids:
            key = f"prompt_task_cb_{tid}"
            if key not in self.state.state:
                self.state.state[key] = (tid in self.state.get("prompt_selected_task_ids"))
    
    def initialize_prompt_config(self):
        """Initialize prompt configuration on startup."""
        cfg = self.state.get("prompt_config")
        if cfg is None:
            cfg = self.get_default_prompt_config()
        self.state.set("prompt_config", cfg)
        
        task_ids = [t.get('id') for t in cfg.get('tasks', []) if t.get('id')]
        if not self.state.get("prompt_ui").get('default_selected_task_ids'):
            pui = self.state.get("prompt_ui")
            pui['default_selected_task_ids'] = task_ids
            self.state.set("prompt_ui", pui)
        
        if not self.state.get("prompt_selected_task_ids"):
            self.state.set("prompt_selected_task_ids", list(self.state.get("prompt_ui").get('default_selected_task_ids', task_ids)))

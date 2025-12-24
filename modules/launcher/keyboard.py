from gi.repository import Gdk, Gtk

from .launcher_modes import (
    MODE_EMOJI,
    MODE_NORMAL,
    MODE_PLACEHOLDERS,
    MODE_SHORTCUTS,
    MODE_WEB,
)


class KeyboardController:
    """Handles keyboard input and mode switching"""

    def __init__(self, launcher):
        self._launcher = launcher
        self._setup_controller()

    def _setup_controller(self):
        """Setup GTK keyboard event controller"""
        keyc = Gtk.EventControllerKey()
        keyc.connect("key-pressed", self._on_key_pressed)
        self._launcher.add_controller(keyc)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard events"""
        alt = state & Gdk.ModifierType.ALT_MASK

        # Alt + Arrow keys for mode cycling
        if alt and keyval == Gdk.KEY_Left:
            return self._cycle_mode(-1)
        elif alt and keyval == Gdk.KEY_Right:
            return self._cycle_mode(1)

        # Alt + letter shortcuts
        if alt:
            keyname = Gdk.keyval_name(keyval)
            if not keyname:
                return False

            key = keyname.lower()
            if key in MODE_SHORTCUTS:
                return self._toggle_mode(MODE_SHORTCUTS[key])

        return False

    def _toggle_mode(self, mode: str) -> bool:
        """Toggle between normal and specific mode"""
        if self._launcher._mode == mode:
            self._launcher._mode = MODE_NORMAL
        else:
            self._launcher._mode = mode

        self._launcher._entry.placeholder_text = MODE_PLACEHOLDERS[self._launcher._mode]
        self._launcher._last_results_key = None

        self._launcher._debounced_search(0.04)

        return True

    def _cycle_mode(self, direction: int) -> bool:
        """Cycle through modes with Alt+Arrow"""
        mode_order = [MODE_NORMAL, MODE_EMOJI, MODE_WEB]

        try:
            current_idx = mode_order.index(self._launcher._mode)
        except ValueError:
            current_idx = 0

        new_idx = (current_idx + direction) % len(mode_order)
        self._launcher._mode = mode_order[new_idx]

        self._launcher._entry.placeholder_text = MODE_PLACEHOLDERS[self._launcher._mode]
        self._launcher._last_results_key = None

        if self._launcher._entry.text.strip():
            self._launcher._debounced_search(0.04)
        else:
            self._launcher._results.child = []
            self._launcher._results_container.visible = False

        return True

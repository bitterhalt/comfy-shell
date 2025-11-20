"""
Audio Menu Window - Popup window that holds the audio menu revealer
"""

from ignis import widgets
from modules.bar.widgets.audio_menu import AudioMenuRevealer


class AudioMenuWindow(widgets.Window):
    """Popup window for audio menu"""

    def __init__(self, monitor: int = 0):
        self._menu = AudioMenuRevealer()

        # Container positioned at top-right
        container = widgets.Box(
            vertical=True,
            valign="start",
            halign="end",
            css_classes=["audio-menu-window-container"],
            child=[self._menu],
        )

        super().__init__(
            visible=False,
            anchor=["top", "right"],
            monitor=monitor,
            namespace="ignis_AUDIO_MENU",
            layer="overlay",
            css_classes=["audio-menu-window"],
            child=container,
            popup=True,
        )

        # Auto-hide when menu is hidden
        self._menu.connect("notify::reveal-child", self._on_reveal_change)

    def _on_reveal_change(self, *args):
        """Hide window when menu revealer closes"""
        if not self._menu.reveal_child:
            from ignis import utils

            utils.Timeout(
                self._menu.transition_duration, lambda: setattr(self, "visible", False)
            )

    def toggle(self):
        """Toggle menu visibility"""
        if not self.visible:
            # Show window first, then reveal menu
            self.visible = True
            from ignis import utils

            utils.Timeout(10, lambda: self._menu.set_reveal_child(True))
        else:
            # Hide menu, window will auto-hide after transition
            self._menu.set_reveal_child(False)


# Global instance
_audio_menu_window = None


def get_audio_menu_window():
    """Get or create audio menu window"""
    global _audio_menu_window
    if _audio_menu_window is None:
        _audio_menu_window = AudioMenuWindow()
    return _audio_menu_window


def toggle_audio_menu():
    """Toggle audio menu"""
    window = get_audio_menu_window()
    window.toggle()

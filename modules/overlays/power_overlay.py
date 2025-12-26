import asyncio

from gi.repository import Gdk

from ignis import utils, widgets
from ignis.window_manager import WindowManager

wm = WindowManager.get_default()


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


class ConfirmDialog(widgets.Window):
    """Keyboard-friendly confirmation dialog"""

    def __init__(self, title: str, message: str, on_confirm=None, on_cancel=None):
        self.on_confirm_callback = on_confirm
        self.on_cancel_callback = on_cancel

        # Title
        title_label = widgets.Label(
            label=title,
            css_classes=["confirm-dialog-title"],
        )

        # Message
        message_label = widgets.Label(
            label=message,
            css_classes=["confirm-dialog-message"],
        )

        # Cancel button
        cancel_btn = widgets.Button(
            label="Cancel",
            css_classes=["confirm-dialog-btn", "confirm-dialog-cancel"],
            on_click=lambda *_: self._cancel(),
            can_focus=True,
        )

        # Confirm button
        confirm_btn = widgets.Button(
            label="Confirm",
            css_classes=["confirm-dialog-btn", "confirm-dialog-confirm"],
            on_click=lambda *_: self._confirm(),
            can_focus=True,
        )

        # Buttons box
        buttons_box = widgets.Box(
            spacing=12,
            halign="center",
            child=[cancel_btn, confirm_btn],
        )

        # Content box
        content_box = widgets.Box(
            vertical=True,
            spacing=24,
            css_classes=["confirm-dialog-content"],
            child=[
                title_label,
                message_label,
                buttons_box,
            ],
        )

        # Center the content
        centered = widgets.Box(
            valign="center",
            halign="center",
            child=[content_box],
        )

        # Background button to close on click
        background_btn = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["confirm-dialog-background"],
            on_click=lambda *_: self._cancel(),
        )

        # Use Overlay like your other modules
        root = widgets.Overlay(
            child=background_btn,
            overlays=[centered],
        )

        super().__init__(
            visible=True,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_CONFIRM_DIALOG",
            exclusivity="ignore",
            layer="overlay",
            popup=True,
            css_classes=["confirm-dialog-window"],
            child=root,
            kb_mode="exclusive",
        )

        # Setup keyboard controller
        self._setup_keyboard_controller()

        # Focus confirm button by default
        confirm_btn.grab_focus()

    def _setup_keyboard_controller(self):
        """Setup keyboard event controller for GTK4"""
        from gi.repository import Gtk

        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard shortcuts"""
        keyname = Gdk.keyval_name(keyval)

        if keyname == "Escape":
            self._cancel()
            return True
        elif keyname in ["Return", "KP_Enter"]:
            self._confirm()
            return True
        elif keyname.lower() == "y":
            self._confirm()
            return True
        elif keyname.lower() == "n":
            self._cancel()
            return True

        return False

    def _confirm(self):
        """Handle confirm action"""
        if self.on_confirm_callback:
            self.on_confirm_callback()
        self.close()

    def _cancel(self):
        """Handle cancel action"""
        if self.on_cancel_callback:
            self.on_cancel_callback()
        self.close()


def confirm_dialog(title: str, message: str, on_confirm=None, on_cancel=None):
    """Show a confirmation dialog"""
    return ConfirmDialog(title, message, on_confirm, on_cancel)


class PowerOverlay(widgets.Window):
    """Shadowplay-style power menu overlay"""

    def __init__(self):
        # Lock button
        lock_btn = widgets.Button(
            css_classes=["power-overlay-btn"],
            on_click=lambda *_: self._lock(),
            can_focus=True,
            child=widgets.Box(
                vertical=True,
                spacing=8,
                child=[
                    widgets.Icon(
                        image="system-lock-screen-symbolic",
                        pixel_size=48,
                    ),
                    widgets.Label(
                        label="[L]ock",
                        css_classes=["power-overlay-label"],
                    ),
                ],
            ),
        )

        # Logout button
        logout_btn = widgets.Button(
            css_classes=["power-overlay-btn"],
            on_click=lambda *_: self._logout(),
            can_focus=True,
            child=widgets.Box(
                vertical=True,
                spacing=8,
                child=[
                    widgets.Icon(
                        image="system-log-out-symbolic",
                        pixel_size=48,
                    ),
                    widgets.Label(
                        label="[E]xit",
                        css_classes=["power-overlay-label"],
                    ),
                ],
            ),
        )

        # Suspend button
        suspend_btn = widgets.Button(
            css_classes=["power-overlay-btn"],
            on_click=lambda *_: self._suspend(),
            can_focus=True,
            child=widgets.Box(
                vertical=True,
                spacing=8,
                child=[
                    widgets.Icon(
                        image="media-playback-pause-symbolic",
                        pixel_size=48,
                    ),
                    widgets.Label(
                        label="z[Z]zz",
                        css_classes=["power-overlay-label"],
                    ),
                ],
            ),
        )

        # Reboot button
        reboot_btn = widgets.Button(
            css_classes=["power-overlay-btn", "power-overlay-btn-danger"],
            on_click=lambda *_: self._reboot(),
            can_focus=True,
            child=widgets.Box(
                vertical=True,
                spacing=8,
                child=[
                    widgets.Icon(
                        image="system-reboot-symbolic",
                        css_classes=["power-warning-icon"],
                        pixel_size=48,
                    ),
                    widgets.Label(
                        label="[R]eboot",
                        css_classes=["power-overlay-label"],
                    ),
                ],
            ),
        )

        # Shutdown button
        shutdown_btn = widgets.Button(
            css_classes=["power-overlay-btn", "power-overlay-btn-danger"],
            on_click=lambda *_: self._shutdown(),
            can_focus=True,
            child=widgets.Box(
                vertical=True,
                spacing=8,
                child=[
                    widgets.Icon(
                        image="system-shutdown-symbolic",
                        css_classes=["power-warning-icon"],
                        pixel_size=48,
                    ),
                    widgets.Label(
                        label="[S]hutdown",
                        css_classes=["power-overlay-label"],
                    ),
                ],
            ),
        )

        buttons_container = widgets.Box(
            vertical=True,
            valign="center",
            halign="center",
            css_classes=["power-overlay"],
            child=[
                widgets.Box(
                    spacing=24,
                    halign="center",
                    css_classes=["power-overlay-buttons"],
                    child=[
                        lock_btn,
                        logout_btn,
                        suspend_btn,
                        reboot_btn,
                        shutdown_btn,
                    ],
                )
            ],
        )

        overlay_btn = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["power-overlay-background"],
            on_click=lambda *_: self.toggle(),
        )

        root_overlay = widgets.Overlay(
            child=overlay_btn,
            overlays=[buttons_container],
        )

        super().__init__(
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_POWER_OVERLAY",
            exclusivity="ignore",
            layer="overlay",
            popup=True,
            css_classes=["power-overlay-window"],
            child=root_overlay,
            kb_mode="exclusive",
        )

        # Setup keyboard controller
        self._setup_keyboard_controller()

    def _setup_keyboard_controller(self):
        """Setup keyboard event controller for GTK4"""
        from gi.repository import Gtk

        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard shortcuts"""
        keyname = Gdk.keyval_name(keyval)

        # Escape to close
        if keyname == "Escape":
            self.toggle()
            return True

        # L - Lock
        elif keyname.lower() == "l":
            self._lock()
            return True

        # E - Exit (logout)
        elif keyname.lower() == "e":
            self._logout()
            return True

        # Z - Sleep (suspend)
        elif keyname.lower() == "z":
            self._suspend()
            return True

        # R - Reboot
        elif keyname.lower() == "r":
            self._reboot()
            return True

        # S - Shutdown
        elif keyname.lower() == "s":
            self._shutdown()
            return True

        return False

    def toggle(self):
        """Toggle overlay visibility"""
        self.visible = not self.visible

    def _lock(self):
        """Lock the screen"""
        exec_async("hyprlock")
        self.toggle()

    def _logout(self):
        """Logout with confirmation"""
        self.toggle()
        confirm_dialog(
            "Logout",
            "Are you sure you want to log out?",
            on_confirm=lambda: exec_async("loginctl terminate-user $USER"),
        )

    def _suspend(self):
        """Suspend the system"""
        exec_async("systemctl suspend")
        self.toggle()

    def _reboot(self):
        """Reboot with confirmation"""
        self.toggle()
        confirm_dialog(
            "Reboot System",
            "Are you sure you want to reboot?",
            on_confirm=lambda: exec_async("systemctl reboot"),
        )

    def _shutdown(self):
        """Shutdown with confirmation"""
        self.toggle()
        confirm_dialog(
            "Power Off",
            "Are you sure you want to shut down?",
            on_confirm=lambda: exec_async("systemctl poweroff"),
        )

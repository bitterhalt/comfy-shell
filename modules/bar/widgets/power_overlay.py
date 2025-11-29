"""
Power Menu Overlay - Shadowplay-style power options
Provides quick access to lock, logout, suspend, reboot, and shutdown
"""

import asyncio

from ignis import utils, widgets


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


def confirm_dialog(title: str, message: str, on_confirm):
    """Confirmation dialog for destructive actions"""
    dialog = widgets.Window(
        popup=True,
        layer="overlay",
        namespace="ignis_power_confirm_dialog",
        anchor=["top", "bottom", "left", "right"],
        visible=True,
        css_classes=["confirm-dialog"],
        child=widgets.Box(
            valign="center",
            halign="center",
            child=[
                widgets.Box(
                    vertical=True,
                    spacing=12,
                    css_classes=["confirm-card"],
                    child=[
                        widgets.Label(
                            label=title,
                            css_classes=["confirm-title"],
                        ),
                        widgets.Label(
                            label=message,
                            css_classes=["confirm-message"],
                            wrap=True,
                        ),
                        widgets.Box(
                            spacing=8,
                            halign="center",
                            child=[
                                widgets.Button(
                                    child=widgets.Label(label="Cancel"),
                                    css_classes=["confirm-btn", "confirm-cancel"],
                                    on_click=lambda *_: dialog.close(),
                                ),
                                widgets.Button(
                                    child=widgets.Label(label="Confirm"),
                                    css_classes=["confirm-btn", "confirm-ok"],
                                    on_click=lambda *_: (dialog.close(), on_confirm()),
                                ),
                            ],
                        ),
                    ],
                )
            ],
        ),
    )
    return dialog


class PowerOverlay(widgets.Window):
    """Shadowplay-style power menu overlay"""

    def __init__(self):
        # Lock button
        lock_icon = widgets.Icon(
            image="system-lock-screen-symbolic",
            pixel_size=48,
        )

        lock_label = widgets.Label(
            label="Lock",
            css_classes=["power-overlay-label"],
        )

        lock_btn = widgets.Button(
            css_classes=["power-overlay-btn"],
            on_click=lambda *_: self._lock(),
            can_focus=True,
            child=widgets.Box(
                vertical=True,
                spacing=8,
                child=[lock_icon, lock_label],
            ),
        )

        # Logout button
        logout_icon = widgets.Icon(
            image="system-log-out-symbolic",
            pixel_size=48,
        )

        logout_label = widgets.Label(
            label="Logout",
            css_classes=["power-overlay-label"],
        )

        logout_btn = widgets.Button(
            css_classes=["power-overlay-btn"],
            on_click=lambda *_: self._logout(),
            can_focus=True,
            child=widgets.Box(
                vertical=True,
                spacing=8,
                child=[logout_icon, logout_label],
            ),
        )

        # Suspend button
        suspend_icon = widgets.Icon(
            image="media-playback-pause-symbolic",
            pixel_size=48,
        )

        suspend_label = widgets.Label(
            label="Suspend",
            css_classes=["power-overlay-label"],
        )

        suspend_btn = widgets.Button(
            css_classes=["power-overlay-btn"],
            on_click=lambda *_: self._suspend(),
            can_focus=True,
            child=widgets.Box(
                vertical=True,
                spacing=8,
                child=[suspend_icon, suspend_label],
            ),
        )

        # Reboot button
        reboot_icon = widgets.Icon(
            image="system-reboot-symbolic",
            pixel_size=48,
        )

        reboot_label = widgets.Label(
            label="Reboot",
            css_classes=["power-overlay-label"],
        )

        reboot_btn = widgets.Button(
            css_classes=["power-overlay-btn-danger"],
            on_click=lambda *_: self._reboot(),
            can_focus=True,
            child=widgets.Box(
                vertical=True,
                spacing=8,
                child=[reboot_icon, reboot_label],
            ),
        )

        # Shutdown button
        shutdown_icon = widgets.Icon(
            image="system-shutdown-symbolic",
            pixel_size=48,
        )

        shutdown_label = widgets.Label(
            label="Shutdown",
            css_classes=["power-overlay-label"],
        )

        shutdown_btn = widgets.Button(
            css_classes=["power-overlay-btn-danger"],
            on_click=lambda *_: self._shutdown(),
            can_focus=True,
            child=widgets.Box(
                vertical=True,
                spacing=8,
                child=[shutdown_icon, shutdown_label],
            ),
        )

        # Main content box
        buttons_box = widgets.Box(
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

        content = widgets.Box(
            vertical=True,
            valign="center",
            halign="center",
            css_classes=["power-overlay"],
            child=[buttons_box],
        )

        # Click outside to close
        overlay_btn = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["power-overlay-background"],
            on_click=lambda *_: self.toggle(),
        )

        root_overlay = widgets.Overlay(
            child=overlay_btn,
            overlays=[content],
        )

        super().__init__(
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            namespace="ignis_POWER_OVERLAY",
            layer="overlay",
            popup=True,
            css_classes=["power-overlay-window"],
            child=root_overlay,
            kb_mode="exclusive",
        )

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
            on_confirm=lambda: exec_async("hyprctl dispatch exit 0"),
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


# Global instance
_power_overlay = None


def get_power_overlay():
    """Get or create power overlay"""
    global _power_overlay
    if _power_overlay is None:
        _power_overlay = PowerOverlay()
    return _power_overlay


def toggle_power_overlay():
    """Toggle power overlay"""
    get_power_overlay().toggle()

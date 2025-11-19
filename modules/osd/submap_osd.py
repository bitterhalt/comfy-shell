"""
Submap OSD - Shows Hyprland submap changes
Displays current submap (resize, move, etc.) with auto-dismiss
"""

import asyncio
import os

from ignis import widgets
from ignis.services.hyprland import HyprlandService

hypr = HyprlandService.get_default()

_osd_window = None


class SubmapOSD(widgets.Window):
    """Minimal submap indicator OSD"""

    def __init__(self):
        # Submap label
        self._label = widgets.Label(
            css_classes=["submap-osd-label"],
        )

        # Icon - CHANGED TO widgets.Icon
        self._icon = widgets.Icon(
            image="",
            pixel_size=24,  # Set a size for the symbolic icon
            css_classes=["submap-osd-icon"],
        )

        # Container
        content = widgets.Box(
            css_classes=["submap-osd"],
            spacing=12,
            child=[self._icon, self._label],
        )

        super().__init__(
            layer="overlay",
            anchor=["top"],
            namespace="ignis_SUBMAP_OSD",
            visible=False,
            css_classes=["submap-osd-window"],
            child=content,
        )

        # Start listening to Hyprland events
        if hypr.is_available:
            self._start_listener()

    def _start_listener(self):
        """Start listening to Hyprland socket for submap events"""

        async def listen():
            try:
                # Get Hyprland socket path from environment
                runtime_dir = os.getenv("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
                hypr_instance = os.getenv("HYPRLAND_INSTANCE_SIGNATURE")

                if not hypr_instance:
                    print("Submap OSD: HYPRLAND_INSTANCE_SIGNATURE not found")
                    return

                # Using the command socket (.socket2.sock) for asynchronous events
                socket_path = f"{runtime_dir}/hypr/{hypr_instance}/.socket2.sock"

                # Check if socket exists
                if not os.path.exists(socket_path):
                    print(f"Submap OSD: Socket not found at {socket_path}")
                    return

                # Listen for events using socat
                proc = await asyncio.create_subprocess_exec(
                    "socat",
                    "-U",
                    "-",
                    f"UNIX-CONNECT:{socket_path}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break

                    line = line.decode().strip()

                    # Check for submap event
                    if line.startswith("submap>>"):
                        submap = line.split(">>", 1)[1] if ">>" in line else ""
                        self._on_submap_change(submap)

            except Exception as e:
                print(f"Submap listener error: {e}")

        # Start listener task
        asyncio.create_task(listen())

    def _on_submap_change(self, submap: str):
        """Handle submap change"""
        # Hide if default or empty
        if not submap or submap == "default":
            self.visible = False
            return

        # Update icon based on submap
        icon_name = self._get_icon_for_submap(submap)
        # CHANGED: Use set_from_icon_name for widgets.Icon
        self._icon.set_from_icon_name(icon_name)

        # Update label
        self._label.set_label(submap.upper())

        # Show OSD (stays visible until submap exits)
        self.visible = True

    def _get_icon_for_submap(self, submap: str) -> str:
        """Get appropriate icon for submap"""
        submap_lower = submap.lower()

        # Common submap icons (Using standard symbolic icons)
        icons = {
            "resize": "window-resize-symbolic",
            "move": "window-move-symbolic",
            "gaps": "view-grid-symbolic",  # Layout/tiling representation
            "float": "window-restore-symbolic",
            "special": "view-grid-symbolic",
            "window": "window-new-symbolic",
        }

        # Check if submap contains any keyword
        for keyword, icon in icons.items():
            if keyword in submap_lower:
                return icon

        # Default keyboard icon
        return "input-keyboard-symbolic"


def init_submap_osd():
    """Initialize submap OSD (call once at startup)"""
    global _osd_window
    if _osd_window is None and hypr.is_available:
        _osd_window = SubmapOSD()


def show_submap_osd(message: str):
    """
    Manually show submap OSD with custom message
    Useful for testing or custom submaps
    """
    if _osd_window:
        _osd_window._label.set_label(message.upper())
        # CHANGED: Use set_from_icon_name for widgets.Icon
        _osd_window._icon.set_from_icon_name("input-keyboard-symbolic")
        _osd_window.visible = True


def hide_submap_osd():
    """Manually hide submap OSD"""
    if _osd_window:
        _osd_window.visible = False

"""
Submap OSD - Pure asyncio Hyprland event listener using .socket2.sock
"""

import asyncio
import os

from ignis import widgets
from ignis.services.hyprland import HyprlandService

hypr = HyprlandService.get_default()
_osd_window = None

EVENT_SOCKET_NAME = ".socket2.sock"


class SubmapOSD(widgets.Window):
    """Minimal submap indicator OSD using Hyprland event IPC"""

    def __init__(self):
        self._reader = None
        self._writer = None
        self._listen_task = None

        # UI
        self._label = widgets.Label(css_classes=["submap-osd-label"])
        self._icon = widgets.Icon(
            image="input-keyboard-symbolic",
            pixel_size=24,
            css_classes=["submap-osd-icon"],
        )

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

        if hypr.is_available:
            self._start_async_listener()

    def _start_async_listener(self):
        if self._listen_task is None:
            self._listen_task = asyncio.create_task(self._event_loop())

    async def _connect_socket(self):
        """Connect to Hyprland .socket2.sock using pure asyncio."""
        try:
            runtime = os.getenv("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
            instance = os.getenv("HYPRLAND_INSTANCE_SIGNATURE")

            if not instance:
                print("Submap OSD: HYPRLAND_INSTANCE_SIGNATURE not found")
                return False

            socket_path = f"{runtime}/hypr/{instance}/{EVENT_SOCKET_NAME}"

            if not os.path.exists(socket_path):
                print(f"Submap OSD: Event socket missing at {socket_path}")
                return False

            self._reader, self._writer = await asyncio.open_unix_connection(socket_path)
            print("Submap OSD: Connected to Hyprland (.socket2.sock)")
            return True

        except Exception as e:
            print(f"Submap OSD: Connection error: {e}")
            return False

    async def _event_loop(self):
        """Main loop: connect → read → reconnect on failure."""
        while True:
            connected = await self._connect_socket()
            if not connected:
                await asyncio.sleep(1)
                continue

            try:
                while True:
                    line = await self._reader.readline()
                    if not line:
                        raise ConnectionError("EOF on socket")

                    line = line.decode().strip()

                    if line.startswith("submap>>"):
                        submap = line.split(">>", 1)[1]
                        self._on_submap_change(submap)

            except Exception as e:
                print(f"Submap OSD: Event loop error: {e}")

            await self._cleanup_socket()
            await asyncio.sleep(1)

    async def _cleanup_socket(self):
        try:
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
        except Exception:
            pass
        self._reader = None
        self._writer = None

    def _on_submap_change(self, submap: str):
        if not submap or submap == "default":
            self.visible = False
            return

        self._icon.set_from_icon_name("input-keyboard-symbolic")
        self._label.set_label(submap.upper())
        self.visible = True


def init_submap_osd():
    global _osd_window
    if _osd_window is None and hypr.is_available:
        _osd_window = SubmapOSD()


def show_submap_osd(message: str):
    if _osd_window:
        _osd_window._label.set_label(message.upper())
        _osd_window._icon.set_from_icon_name("input-keyboard-symbolic")
        _osd_window.visible = True


def hide_submap_osd():
    if _osd_window:
        _osd_window.visible = False

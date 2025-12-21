import asyncio

from ignis import utils, widgets
from ignis.services.recorder import RecorderService
from ignis.window_manager import WindowManager

from settings import config

wm = WindowManager.get_default()
recorder = RecorderService.get_default()


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


class RecordingOverlay(widgets.Window):
    """Shadowplay-style recording overlay"""

    def __init__(self):
        # Screenshot button
        self._screenshot_icon = widgets.Icon(
            image="camera-photo-symbolic",
            pixel_size=48,
        )

        self._screenshot_label = widgets.Label(
            label="Screenshot",
            css_classes=["overlay-label"],
        )

        self._screenshot_btn = widgets.Button(
            css_classes=["overlay-btn"],
            on_click=lambda x: self._take_screenshot(),
            can_focus=True,
            child=widgets.Box(
                vertical=True,
                spacing=8,
                child=[self._screenshot_icon, self._screenshot_label],
            ),
        )

        # Screenshot Region button
        self._screenshot_region_icon = widgets.Icon(
            image="image-crop-symbolic",
            pixel_size=48,
        )

        self._screenshot_region_label = widgets.Label(
            label="Screenshot Region",
            css_classes=["overlay-label"],
        )

        self._screenshot_region_btn = widgets.Button(
            css_classes=["overlay-btn"],
            on_click=lambda x: self._screenshot_region(),
            can_focus=True,
            child=widgets.Box(
                vertical=True,
                spacing=8,
                child=[self._screenshot_region_icon, self._screenshot_region_label],
            ),
        )

        self._record_screen_icon = widgets.Icon(
            image="media-record-symbolic",
            pixel_size=48,
        )

        self._record_screen_label = widgets.Label(
            label="Record",
            css_classes=["overlay-label"],
        )

        self._record_screen_btn = widgets.Button(
            css_classes=["overlay-btn"],
            on_click=lambda x: self._record_screen(),
            can_focus=True,
            child=widgets.Box(
                vertical=True,
                spacing=8,
                child=[self._record_screen_icon, self._record_screen_label],
            ),
        )

        # Record Region button
        self._record_region_icon = widgets.Icon(
            image="edit-select-all-symbolic",
            pixel_size=48,
        )

        self._record_region_label = widgets.Label(
            label="Record Region",
            css_classes=["overlay-label"],
        )

        self._record_region_btn = widgets.Button(
            css_classes=["overlay-btn"],
            on_click=lambda x: self._record_region(),
            can_focus=True,
            child=widgets.Box(
                vertical=True,
                spacing=8,
                child=[self._record_region_icon, self._record_region_label],
            ),
        )

        # Main content box
        buttons_box = widgets.Box(
            spacing=24,
            halign="center",
            css_classes=["overlay-buttons"],
            child=[
                self._screenshot_btn,
                self._screenshot_region_btn,
                self._record_screen_btn,
                self._record_region_btn,
            ],
        )

        content = widgets.Box(
            vertical=True,
            valign="center",
            halign="center",
            css_classes=["recording-overlay"],
            child=[buttons_box],
        )

        # Click outside to close
        overlay_btn = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["overlay-background"],
            on_click=lambda x: self.toggle(),
        )

        root_overlay = widgets.Overlay(
            child=overlay_btn,
            overlays=[content],
        )

        super().__init__(
            monitor=config.ui.primary_monitor,
            visible=False,
            anchor=["top", "bottom", "left", "right"],
            exclusivity="ignore",
            namespace="ignis_RECORDING_OVERLAY",
            layer="overlay",
            popup=True,
            css_classes=["recording-overlay-window"],
            child=root_overlay,
            kb_mode="exclusive",
        )

        recorder.connect("recording_started", lambda x: self._update_recording_state())
        recorder.connect("recording_stopped", lambda x: self._update_recording_state())

        # Initial state
        self._update_recording_state()

    def _update_recording_state(self):
        """Update UI based on recording state"""
        is_recording = self._is_recording()

        if is_recording:
            self._record_screen_icon.image = "media-playback-stop-symbolic"
            self._record_screen_label.label = "Stop Recording"
            self._record_screen_btn.remove_css_class("overlay-btn")
            self._record_screen_btn.add_css_class("overlay-btn-stop")
        else:
            self._record_screen_icon.image = "media-record-symbolic"
            self._record_screen_label.label = "Record"
            self._record_screen_btn.remove_css_class("overlay-btn-stop")
            self._record_screen_btn.add_css_class("overlay-btn")

    def _is_recording(self):
        """Check if any recording is active"""
        from modules.recorder.recorder import is_recording

        return is_recording()

    def toggle(self):
        """Toggle overlay visibility"""
        self.visible = not self.visible

    def _take_screenshot(self):
        """Take fullscreen screenshot"""
        exec_async("wl-shot --fullscreen")
        self.toggle()

    def _screenshot_region(self):
        """Take region screenshot"""
        exec_async("wl-shot --region")
        self.toggle()

    def _record_screen(self):
        """Start screen recording or stop if already recording"""
        from ignis.command_manager import CommandManager

        cmd_manager = CommandManager.get_default()

        if self._is_recording():
            cmd_manager.run_command("recorder-stop")
        else:
            cmd_manager.run_command("recorder-record-screen")

        self.toggle()

    def _record_region(self):
        """Start region recording"""
        from ignis.command_manager import CommandManager

        cmd_manager = CommandManager.get_default()
        cmd_manager.run_command("recorder-record-region")
        self.toggle()


def toggle_recording_overlay():
    try:
        wm.toggle_window("ignis_RECORDING_OVERLAY")
    except:
        RecordingOverlay()
        wm.toggle_window("ignis_RECORDING_OVERLAY")

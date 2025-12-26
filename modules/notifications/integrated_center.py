"""
Integrated center
"""

from ignis import utils, widgets
from ignis.options import options
from ignis.window_manager import WindowManager
from modules.notifications.integrated_center_notifications import NotificationList
from modules.notifications.integrated_center_tasks import TaskList
from modules.notifications.integrated_center_weather import WeatherPill
from modules.notifications.media import MediaCenterWidget
from settings import config

wm = WindowManager.get_default()


class IntegratedCenter(widgets.Window):

    def __init__(self):
        # -------------------------------------------------------
        # LEFT COLUMN: NOTIFICATIONS + MEDIA
        # -------------------------------------------------------

        # Media pill
        self._media_pill = MediaCenterWidget()

        # Notification list
        self._notification_list = NotificationList()

        # DND toggle
        dnd_switch = widgets.Switch(
            active=options.notifications.bind("dnd"),
            on_change=lambda _, s: options.notifications.set_dnd(s),
        )

        dnd_box = widgets.Box(
            spacing=8,
            css_classes=["dnd-box"],
            hexpand=True,
            halign="start",
            child=[
                widgets.Label(label="Do Not Disturb", css_classes=["dnd-label"]),
                dnd_switch,
            ],
        )

        # Clear button
        clear_btn = widgets.Button(
            child=widgets.Label(label="Clear All"),
            css_classes=["header-action-btn"],
            on_click=lambda *_: self._notification_list.clear_all(),
        )

        left_column = widgets.Box(
            vertical=True,
            css_classes=["left-column"],
            child=[
                self._media_pill,
                self._notification_list.scroll,
                widgets.Box(
                    spacing=8,
                    halign="fill",
                    valign="end",
                    css_classes=["left-bottom-bar"],
                    child=[dnd_box, clear_btn],
                ),
            ],
        )

        # -------------------------------------------------------
        # RIGHT COLUMN: WEATHER + CALENDAR + TASKS
        # -------------------------------------------------------

        # Weather pill
        self._weather_pill = WeatherPill()

        # Calendar
        self._calendar = widgets.Calendar(
            css_classes=["center-calendar"],
            show_day_names=True,
            show_heading=False,
        )
        self._calendar_expanded = False

        self._calendar_expander_button = widgets.Button(
            css_classes=["calendar-expander"],
            on_click=lambda *_: self._toggle_calendar(),
            child=widgets.Icon(
                image="pan-down-symbolic",
                pixel_size=16,
                css_classes=["calendar-expander-icon"],
            ),
        )

        self._calendar_box = widgets.Box(
            vertical=True,
            visible=False,
            css_classes=["calendar-box"],
            child=[self._calendar],
        )

        # Task list
        self._task_list = TaskList(on_show_dialog=self._show_dialog)

        right_column = widgets.Box(
            vertical=True,
            css_classes=["right-column"],
            child=[
                self._weather_pill.button,
                self._calendar_expander_button,
                self._calendar_box,
                self._task_list.next_task_box,
                self._task_list.scroll,
            ],
        )

        # -------------------------------------------------------
        # MAIN LAYOUT
        # -------------------------------------------------------

        two_columns = widgets.Box(
            css_classes=["integrated-center"],
            child=[left_column, right_column],
        )
        self._main_content = two_columns

        # Revealer for slide animation
        self._revealer = widgets.Revealer(
            child=two_columns,
            reveal_child=False,
            transition_type="slide_down",
            transition_duration=180,
        )

        # Overlay button
        overlay_button = widgets.Button(
            vexpand=True,
            hexpand=True,
            can_focus=False,
            css_classes=["center-overlay"],
            on_click=lambda x: wm.close_window("ignis_INTEGRATED_CENTER"),
        )

        root_overlay = widgets.Overlay(
            child=overlay_button,
            overlays=[
                widgets.Box(
                    valign="start",
                    halign="center",
                    css_classes=["center-container"],
                    child=[self._revealer],
                )
            ],
        )

        super().__init__(
            monitor=config.ui.integrated_center_monitor,
            visible=False,
            popup=True,
            anchor=["top", "bottom", "left", "right"],
            layer="top",
            namespace="ignis_INTEGRATED_CENTER",
            css_classes=["center-window"],
            child=root_overlay,
            kb_mode="on_demand",
        )

        # Handle visibility changes for reveal animation
        self.connect("notify::visible", self._on_visible_change)

        # Cleanup on destroy
        self.connect("destroy", self._cleanup)

    def _cleanup(self, *_):
        """Cleanup weather pill and task list on destroy"""
        if hasattr(self, "_weather_pill") and self._weather_pill:
            try:
                self._weather_pill.destroy()
            except:
                pass

    def _on_visible_change(self, *_):
        """Handle reveal animation when window opens/closes"""
        if self.visible:
            # Notify task list that we're visible
            self._task_list.set_visible(True)

            utils.Timeout(10, lambda: setattr(self._revealer, "reveal_child", True))
        else:
            # Notify task list that we're hidden
            self._task_list.set_visible(False)

            self._revealer.reveal_child = False

    def _toggle_calendar(self):
        """Toggle calendar visibility"""
        self._calendar_expanded = not self._calendar_expanded
        self._calendar_box.visible = self._calendar_expanded
        self._task_list.scroll.visible = self._calendar_expanded

        icon = "pan-up-symbolic" if self._calendar_expanded else "pan-down-symbolic"
        icon_widget = self._calendar_expander_button.child
        if isinstance(icon_widget, widgets.Icon):
            icon_widget.image = icon

    def _show_dialog(self, dialog):
        """Show a dialog (task add/edit) or return to main content"""
        if dialog is None:
            self._revealer.child = self._main_content
        else:
            dialog.hexpand = True
            dialog.vexpand = False
            self._revealer.child = dialog

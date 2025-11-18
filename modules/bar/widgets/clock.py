import datetime

from ignis import utils, widgets
from ignis.services.notifications import NotificationService
from modules.notifications.integrated_center import toggle_integrated_center

notifications = NotificationService.get_default()


def clock():
    # Visible clock text
    clock_label = widgets.Label(css_classes=["clock"])

    # Clickable wrapper
    clock_button = widgets.Button(
        child=clock_label,
        css_classes=["clock-button"],  # (style inside SCSS to remove button look)
        on_click=lambda *_: toggle_integrated_center(),
    )

    def update(self):
        now = datetime.datetime.now()

        date_str = now.strftime("%A, %d.%m %Y")
        count = len(notifications.notifications)

        tooltip = date_str
        if count > 0:
            tooltip += f"\n\n{count} notification(s)"

        clock_button.set_tooltip_text(tooltip)

        return now.strftime("%H:%M")

    # Bind clock content
    clock_label.set_property(
        "label",
        utils.Poll(60000, update).bind("output"),
    )

    return clock_button

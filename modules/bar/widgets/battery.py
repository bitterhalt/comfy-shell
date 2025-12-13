from ignis import widgets
from ignis.services.upower import UPowerService
from settings import config

upower = UPowerService.get_default()


def battery_widget():
    """Battery indicator with icon and percentage"""
    batteries = [dev for dev in upower.devices if dev.type == "battery"]

    if not batteries:
        return widgets.Box(visible=False)

    battery = batteries[0]

    icon = widgets.Icon(
        image=battery.icon_name,
        pixel_size=22,
    )

    label = widgets.Label(
        label=battery.bind("percentage", lambda p: f"{int(p)}%"),
    )

    container = widgets.Box(
        css_classes=["battery"],
        spacing=4,
        child=[icon, label],
    )

    def update_tooltip(*_):
        status = (
            "Charging"
            if battery.is_charging
            else "Discharging" if battery.is_discharging else "Full"
        )
        time_str = ""

        if battery.is_charging and battery.time_to_full > 0:
            hours = battery.time_to_full // 3600
            mins = (battery.time_to_full % 3600) // 60
            time_str = f"\nTime to full: {hours}h {mins}m"
        elif battery.is_discharging and battery.time_to_empty > 0:
            hours = battery.time_to_empty // 3600
            mins = (battery.time_to_empty % 3600) // 60
            time_str = f"\nTime remaining: {hours}h {mins}m"

        container.set_tooltip_text(
            f"{battery.device_name}\n{status}: {int(battery.percentage)}%{time_str}"
        )

    # Connect to property changes
    battery.connect("notify::percentage", update_tooltip)
    battery.connect("notify::is-charging", update_tooltip)
    battery.connect("notify::is-discharging", update_tooltip)
    battery.connect("notify::time-to-full", update_tooltip)
    battery.connect("notify::time-to-empty", update_tooltip)

    # Initial tooltip
    update_tooltip()

    # Add warning class for low battery
    def update_warning(*_):
        if battery.percentage < config.battery.critical_threshold:
            container.add_css_class("critical")
            container.remove_css_class("warning")
        elif battery.percentage < config.battery.warning_threshold:
            container.add_css_class("warning")
            container.remove_css_class("critical")
        else:
            container.remove_css_class("warning")
            container.remove_css_class("critical")

    # ✅ FIX: Connect and call outside the function
    battery.connect("notify::percentage", update_warning)
    update_warning()

    return container

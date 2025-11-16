import asyncio

from ignis import utils, widgets
from ignis.services.network import NetworkService


# Helper function to execute a shell command asynchronously
def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


# Get service instance and its sub-objects
network = NetworkService.get_default()
vpn = network.vpn
ethernet = network.ethernet
wifi = network.wifi


# --- Helper Functions ---
def safe_get_wifi_ssid():
    if wifi.is_connected and wifi.devices:
        try:
            device = wifi.devices[0]
            ap = device.ap
            return ap.ssid if ap and ap.ssid else "Wi-Fi"
        except (IndexError, AttributeError, TypeError):
            return "Wi-Fi"
    return "Wi-Fi"


def safe_get_ethernet_name():
    if ethernet.is_connected and ethernet.devices:
        try:
            device = ethernet.devices[0]
            return device.name if device.name else "Ethernet"
        except (IndexError, AttributeError, TypeError):
            return "Ethernet"
    return "Ethernet"


# --- Logic Functions to determine output value ---


def determine_icon_name():
    if vpn.is_connected:
        return vpn.icon_name
    if ethernet.is_connected:
        return ethernet.icon_name
    if wifi.is_connected:
        return wifi.icon_name
    return "network-offline-symbolic"


def determine_label_text():
    # This text will be used for the tooltip
    if vpn.is_connected:
        return vpn.active_vpn_id or "VPN"
    if ethernet.is_connected:
        return safe_get_ethernet_name()
    if wifi.is_connected:
        return safe_get_wifi_ssid()
    return "Disconnected"


def determine_visibility():
    return vpn.is_connected or ethernet.is_connected or wifi.is_connected


def network_widget():
    """
    Displays the primary network status (icon only) with tooltip.
    """
    # Properties to monitor for changes
    bind_properties = [
        (vpn, "is_connected"),
        (vpn, "active_vpn_id"),
        (ethernet, "is_connected"),
        (wifi, "is_connected"),
        (wifi, "icon_name"),
    ]

    # 1. Create the widgets
    icon_widget = widgets.Icon(
        image=determine_icon_name(),
        pixel_size=22,
    )

    # Label widget is created to hold the text data, but will NOT be displayed
    label_widget = widgets.Label(
        label=determine_label_text(),
        max_width_chars=15,
        ellipsize="end",
    )

    # Inner box contains ONLY the icon
    inner_box = widgets.Box(
        spacing=4,
        child=[icon_widget],  # <-- ICON ONLY
    )

    # 2. Use a Button for click action and set the dynamic tooltip
    network_button = widgets.Button(
        css_classes=["network-box"],
        on_click=lambda *_: exec_async("nm-connection-editor"),
        visible=determine_visibility(),
        child=inner_box,
        # Bind the tooltip text to the label widget's text
        tooltip_text=label_widget.bind("label"),
    )

    # 3. Define the callback to update all widget properties
    def update_widgets(*args):
        icon_widget.set_property("image", determine_icon_name())
        # Updating the label text automatically updates the button's tooltip
        label_widget.set_property("label", determine_label_text())
        network_button.set_property("visible", determine_visibility())

    # 4. Manually connect the update function to all necessary signals
    for source_object, prop_name in bind_properties:
        signal_name = f"notify::{prop_name.replace('_', '-')}"
        source_object.connect(signal_name, update_widgets)

    return network_button

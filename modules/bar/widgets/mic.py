from ignis import widgets
from ignis.services.audio import AudioService

audio = AudioService.get_default()


def mic_icon():
    mic = audio.microphone

    # If no microphone exists
    if not mic:
        return widgets.Box(visible=False)

    # Create icon
    icon = widgets.Icon(
        image=mic.icon_name,
        pixel_size=18,
    )

    # Initial tooltip
    percent = int(min(mic.volume, 1.0) * 100)
    icon.set_tooltip_text(f"{mic.description}\nvol: {percent}%")

    # Container (hidden when muted)
    container = widgets.EventBox(
        child=[icon],
        css_classes=["mic-box"],
        visible=not mic.is_muted,
        on_click=lambda *_: toggle_mute(),
    )

    # Toggles mic mute state
    def toggle_mute():
        mic.is_muted = not mic.is_muted

    # Update icon, tooltip, and visibility
    def update(*_):
        percent = int(min(mic.volume, 1.0) * 100)
        icon.set_property("image", mic.icon_name)
        icon.set_tooltip_text(f"{mic.description}\nvol: {percent}%")
        container.set_visible(not mic.is_muted)

    # Connect updates
    mic.connect("notify::volume", update)
    mic.connect("notify::is-muted", update)
    mic.connect("notify::icon-name", update)
    mic.connect("notify::description", update)

    return container

from ignis import widgets
from ignis.services.recorder import RecorderService

recorder = RecorderService.get_default()


def recording_indicator():
    container = widgets.EventBox(
        css_classes=["recording-box"],
        visible=False,
        child=[
            widgets.Label(label="", css_classes=["recording-icon"]),
        ],
        on_click=lambda *_: (recorder.stop_recording() if recorder.active else None),
    )

    icon = container.child[0]

    def on_start(*_):
        icon.set_label("󰻂")
        icon.set_tooltip_text("Recording...\nClick to stop")
        container.set_visible(True)

    def on_stop(*_):
        icon.set_label("")
        icon.set_tooltip_text("")
        container.set_visible(False)

    recorder.connect("recording_started", on_start)
    recorder.connect("recording_stopped", on_stop)

    # Initial state check
    if recorder.active:
        on_start()
    else:
        on_stop()

    return container

import datetime

from ignis import utils, widgets


def clock():
    # 1. Create the widget instance first
    clock_label = widgets.Label(
        css_classes=["clock"],
    )

    # 2. Define the function that updates properties and returns the label string
    def get_time_and_set_tooltip(self):
        now = datetime.datetime.now()

        # Side-Effect: Update the tooltip with the full date
        # Example: "Thursday, November 13, 2025"
        date_str = now.strftime("%A, %d.%m %Y")
        clock_label.set_tooltip_text(date_str)

        # The primary function returns the time string for the 'label' property binding
        return now.strftime("%H:%M")

    # 3. Bind the 'label' property to the output of the Poll object
    clock_label.set_property(
        "label", utils.Poll(1000, get_time_and_set_tooltip).bind("output")
    )

    # 4. Return the widget instance
    return clock_label

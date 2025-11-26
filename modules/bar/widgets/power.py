import asyncio

from ignis import utils, widgets
from ignis.menu_model import IgnisMenuItem, IgnisMenuModel


# ---------------------------------------------------------------
# Async shell runner
# ---------------------------------------------------------------
def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


# ---------------------------------------------------------------
# Confirmation dialog (card-style, matches audio menu)
# ---------------------------------------------------------------
def confirm_dialog(title: str, message: str, on_confirm):
    dialog = widgets.Window(
        popup=True,
        layer="overlay",
        namespace="ignis_confirm_dialog",
        anchor=["top", "bottom", "left", "right"],
        visible=True,
        css_classes=["confirm-dialog"],
        child=widgets.Box(
            valign="center",
            halign="center",
            child=[
                widgets.Box(
                    vertical=True,
                    spacing=12,
                    css_classes=["confirm-card"],
                    child=[
                        widgets.Label(
                            label=title,
                            css_classes=["confirm-title"],
                        ),
                        widgets.Label(
                            label=message,
                            css_classes=["confirm-message"],
                            wrap=True,
                        ),
                        widgets.Box(
                            spacing=8,
                            halign="center",
                            child=[
                                widgets.Button(
                                    child=widgets.Label(label="Cancel"),
                                    css_classes=["confirm-btn", "confirm-cancel"],
                                    on_click=lambda *_: dialog.close(),
                                ),
                                widgets.Button(
                                    child=widgets.Label(label="Confirm"),
                                    css_classes=["confirm-btn", "confirm-ok"],
                                    on_click=lambda *_: (dialog.close(), on_confirm()),
                                ),
                            ],
                        ),
                    ],
                )
            ],
        ),
    )

    return dialog


# ---------------------------------------------------------------
# POWER MENU
# ---------------------------------------------------------------
def power_menu():
    model = IgnisMenuModel(
        # --- Lock ---
        IgnisMenuItem(
            label="Lock",
            on_activate=lambda *_: exec_async("hyprlock"),
        ),
        # --- Suspend ---
        IgnisMenuItem(
            label="Suspend",
            on_activate=lambda *_: exec_async("systemctl suspend"),
        ),
        # --- Reboot ---
        IgnisMenuItem(
            label="Reboot",
            on_activate=lambda *_: confirm_dialog(
                "Reboot System",
                "Are you sure you want to reboot?",
                on_confirm=lambda: exec_async("systemctl reboot"),
            ),
        ),
        # --- Shutdown ---
        IgnisMenuItem(
            label="Shutdown",
            on_activate=lambda *_: confirm_dialog(
                "Power Off",
                "Are you sure you want to shut down?",
                on_confirm=lambda: exec_async("systemctl poweroff"),
            ),
        ),
        # --- Logout ---
        IgnisMenuItem(
            label="Logout",
            on_activate=lambda *_: confirm_dialog(
                "Logout",
                "Are you sure you want to log out?",
                on_confirm=lambda: exec_async("hyprctl dispatch exit 0"),
            ),
        ),
    )

    menu = widgets.PopoverMenu(
        model=model,
        css_classes=["power-menu-popover"],
    )

    return widgets.Button(
        css_classes=["power-menu-button"],
        on_click=lambda *_: menu.popup(),
        child=widgets.Box(
            spacing=6,
            child=[
                widgets.Icon(
                    image="system-shutdown-symbolic",
                    pixel_size=22,
                    css_classes=["power-menu-icon"],
                ),
                menu,
            ],
        ),
    )

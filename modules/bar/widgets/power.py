import asyncio

from ignis import utils, widgets
from ignis.menu_model import IgnisMenuItem, IgnisMenuModel, IgnisMenuSeparator


def exec_async(cmd: str):
    asyncio.create_task(utils.exec_sh_async(cmd))


def power_menu():
    menu = widgets.PopoverMenu(
        model=IgnisMenuModel(
            IgnisMenuItem("Lock", on_activate=lambda *_: exec_async("hyprlock")),
            IgnisMenuSeparator(),
            IgnisMenuItem(
                "Suspend", on_activate=lambda *_: exec_async("systemctl suspend")
            ),
            IgnisMenuItem(
                "Hibernate", on_activate=lambda *_: exec_async("systemctl hibernate")
            ),
            IgnisMenuSeparator(),
            IgnisMenuItem(
                "Reboot", on_activate=lambda *_: exec_async("systemctl reboot")
            ),
            IgnisMenuItem(
                "Shutdown", on_activate=lambda *_: exec_async("systemctl poweroff")
            ),
        )
    )

    return widgets.Button(
        css_classes=["power-menu"],
        on_click=lambda *_: menu.popup(),
        child=widgets.Box(
            child=[
                widgets.Icon(image="system-shutdown-symbolic", pixel_size=22),
                menu,
            ]
        ),
    )

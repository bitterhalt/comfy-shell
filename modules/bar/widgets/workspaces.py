from ignis import widgets
from ignis.services.hyprland import HyprlandService, HyprlandWorkspace
from ignis.services.niri import NiriService, NiriWorkspace

hypr = HyprlandService.get_default()
niri = NiriService.get_default()


def hypr_btn(ws: HyprlandWorkspace):
    label_text = ws.name

    if label_text.isdigit():
        pass
    elif label_text.startswith("special:"):
        clean_name = label_text.split(":")[-1]
        label_text = clean_name[0].upper()
    else:
        label_text = label_text[0].upper()
    btn = widgets.Button(
        css_classes=["ws-btn", "unset"],
        on_click=lambda *_: ws.switch_to(),
        child=widgets.Label(label=label_text),
    )
    if ws.id == hypr.active_workspace.id:
        btn.add_css_class("active")
    return btn


def niri_btn(ws: NiriWorkspace):
    btn = widgets.Button(
        css_classes=["ws-btn", "unset"],
        on_click=lambda *_: ws.switch_to(),
        child=widgets.Label(label=str(ws.idx)),
    )
    if ws.is_active:
        btn.add_css_class("active")
    return btn


def workspace_button(ws):
    if hypr.is_available:
        return hypr_btn(ws)
    elif niri.is_available:
        return niri_btn(ws)
    return widgets.Button(css_classes=["ws-btn", "unset"])


def _scroll_niri(output: str, delta: int):
    active = [w for w in niri.workspaces if w.output == output and w.is_active]
    if not active:
        return
    niri.switch_to_workspace(active[0].idx + delta)


def workspaces(monitor_name: str):
    if hypr.is_available:
        return widgets.EventBox(
            css_classes=["workspaces"],
            spacing=4,
            on_scroll_up=lambda *_: hypr.switch_to_workspace(hypr.active_workspace.id - 1),
            on_scroll_down=lambda *_: hypr.switch_to_workspace(hypr.active_workspace.id + 1),
            child=hypr.bind_many(
                ["workspaces", "active_workspace"],
                transform=lambda ws, active: [
                    workspace_button(w) for w in ws if w.id >= 1 or w.name == "special:scratchpad"
                ],
            ),
        )

    elif niri.is_available:
        return widgets.EventBox(
            css_classes=["workspaces"],
            spacing=4,
            on_scroll_up=lambda *_: _scroll_niri(monitor_name, +1),
            on_scroll_down=lambda *_: _scroll_niri(monitor_name, -1),
            child=niri.bind(
                "workspaces",
                transform=lambda ws: [workspace_button(w) for w in ws if w.output == monitor_name],
            ),
        )

    return widgets.Box(css_classes=["workspaces"])

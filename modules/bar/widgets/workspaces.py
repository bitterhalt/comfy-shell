from ignis import widgets
from ignis.services.hyprland import HyprlandService, HyprlandWorkspace
from ignis.services.niri import NiriService, NiriWorkspace

hypr = HyprlandService.get_default()
niri = NiriService.get_default()


def hypr_btn(ws: HyprlandWorkspace):
    # Use the workspace name, not the ID, to avoid showing large negative numbers.
    label_text = ws.name

    # 1. Check for standard numeric workspaces (e.g., '1', '2', '10')
    if label_text.isdigit():
        # Do nothing, keep the numeric label as is
        pass

    # 2. Check for special workspaces (e.g., 'special:scratchpad')
    # NOTE: This logic applies *after* filtering has occurred in workspaces()
    elif label_text.startswith("special:"):
        # Extracts the actual name (e.g., 'scratchpad') and takes the first letter ('S')
        clean_name = label_text.split(":")[-1]
        label_text = clean_name[0].upper()

    # 3. Handle any other custom named workspace
    else:
        # Take the first letter and capitalize it
        label_text = label_text[0].upper()

    btn = widgets.Button(
        css_classes=["ws-btn"],
        on_click=lambda *_: ws.switch_to(),
        # Use the cleaned-up label_text
        child=widgets.Label(label=label_text),
    )
    if ws.id == hypr.active_workspace.id:
        btn.add_css_class("active")
    return btn


def niri_btn(ws: NiriWorkspace):
    btn = widgets.Button(
        css_classes=["ws-btn"],
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
    return widgets.Button(css_classes=["ws-btn"])


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
            on_scroll_up=lambda *_: hypr.switch_to_workspace(
                hypr.active_workspace.id - 1
            ),
            on_scroll_down=lambda *_: hypr.switch_to_workspace(
                hypr.active_workspace.id + 1
            ),
            child=hypr.bind_many(
                ["workspaces", "active_workspace"],
                transform=lambda ws, active: [
                    workspace_button(w)
                    for w in ws
                    # STRICT FILTER: Only show ID >= 1 OR the specific special workspace(s).
                    if w.id >= 1
                    or w.name
                    == "special:scratchpad"  # <--- ONLY show scratchpad special
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
                transform=lambda ws: [
                    workspace_button(w) for w in ws if w.output == monitor_name
                ],
            ),
        )

    return widgets.Box(css_classes=["workspaces"])

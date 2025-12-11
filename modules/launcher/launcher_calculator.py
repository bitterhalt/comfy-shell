import html

from gi.repository import Gdk

from ignis import widgets


def looks_like_math(text: str) -> bool:
    """Check if text looks like a math expression"""
    return any(c.isdigit() for c in text) and any(op in text for op in "+-*/()^.")


def calculate(expression: str) -> list:
    """Evaluate math expression and return result widget"""
    try:
        expr = expression.replace("^", "**")
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed or c == "*" for c in expr):
            raise ValueError

        result = eval(expr, {"__builtins__": {}}, {})
        if isinstance(result, float):
            result = f"{result:.10f}".rstrip("0").rstrip(".")

        def copy_result(value):
            Gdk.Display.get_default().get_clipboard().set(value)

        btn = widgets.Button(
            css_classes=["calc-result"],
            on_click=lambda *_: copy_result(str(result)),
            child=widgets.Box(
                spacing=12,
                child=[
                    widgets.Label(label="🔢"),
                    widgets.Box(
                        vertical=True,
                        child=[
                            widgets.Label(
                                label=html.escape(expression),
                                use_markup=True,
                            ),
                            widgets.Label(
                                label=f"= {html.escape(str(result))}",
                                use_markup=True,
                            ),
                        ],
                    ),
                ],
            ),
        )

        return [btn]

    except Exception:
        return [widgets.Label(label="Invalid expression", css_classes=["calc-error"])]

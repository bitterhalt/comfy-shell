from .launcher_apps import build_app_index, search_apps
from .launcher_binary import search_binaries
from .launcher_calculator import calculate, looks_like_math
from .launcher_emoji import load_emojis, search_emojis
from .launcher_modes import MODE_EMOJI, MODE_WEB
from .launcher_web import search_web


class SearchCoordinator:
    """Coordinates search across different modes"""

    def __init__(self):
        # Load data
        self._emojis = load_emojis()
        self._app_index = build_app_index()

    def search(self, query: str, mode: str) -> list:
        """
        Search based on current mode and query

        Args:
            query: Search query string
            mode: Current launcher mode

        Returns:
            List of result widgets
        """
        if not query:
            return []

        # Mode-specific search
        if mode == MODE_EMOJI:
            return search_emojis(query, self._emojis)

        if mode == MODE_WEB:
            return search_web(query)

        # Normal mode: check for calculator first
        if query.endswith("=") or looks_like_math(query):
            return calculate(query.rstrip("="))

        # Normal mode: search apps and binaries
        return self._search_normal(query)

    def _search_normal(self, query: str) -> list:
        """
        Search in normal mode: .desktop apps + PATH binaries

        Returns apps first, then binaries
        """
        app_results = search_apps(query, self._app_index)
        bin_results = search_binaries(query)

        # Filter out "no binaries" placeholder if we have app results
        if bin_results and len(bin_results) == 1:
            label_item = bin_results[0]
            if hasattr(label_item, "get_css_classes"):
                classes = label_item.get_css_classes()
            else:
                classes = getattr(label_item, "css_classes", [])
            if "no-results" in classes and app_results:
                bin_results = []

        return app_results + bin_results

    def reload_apps(self):
        """Reload application index (e.g., after app install)"""
        self._app_index = build_app_index()

    def reload_emojis(self):
        """Reload emoji list"""
        self._emojis = load_emojis()

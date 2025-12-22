"""
Signal connection manager to prevent memory leaks
"""

from typing import Callable, List, Tuple

from gi.repository import GObject


class SignalManager:
    """
    Manages signal connections to prevent memory leaks.

    Usage:
        self._signals = SignalManager()
        self._signals.connect(obj, "signal-name", handler)

        # Later:
        self._signals.disconnect_all()
    """

    def __init__(self):
        self._connections: List[Tuple[GObject.Object, int]] = []

    def connect(
        self, obj: GObject.Object, signal: str, handler: Callable, *args
    ) -> int:
        """Connect signal and track it"""
        handler_id = obj.connect(signal, handler, *args)
        self._connections.append((obj, handler_id))
        return handler_id

    def disconnect_all(self):
        """Disconnect all tracked signals"""
        for obj, handler_id in self._connections:
            try:
                obj.disconnect(handler_id)
            except:
                pass  # Object may be destroyed

        self._connections.clear()

    def disconnect_from_object(self, obj: GObject.Object):
        """Disconnect all signals from specific object"""
        remaining = []

        for conn_obj, handler_id in self._connections:
            if conn_obj == obj:
                try:
                    obj.disconnect(handler_id)
                except:
                    pass
            else:
                remaining.append((conn_obj, handler_id))

        self._connections = remaining

    def __del__(self):
        """Cleanup on destruction"""
        self.disconnect_all()

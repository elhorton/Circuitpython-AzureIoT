"""A generic base class listener for events
"""


class Listener:
    """A class that can listen for events and make callbacks
    """

    def __init__(self):
        self._events = {}

    def on(self, event_name: str, callback):
        """Subscribe to a named event, and when that event happens callback is called
        """
        self._events[event_name] = callback

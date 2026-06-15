"""Dev-only tools — scratch utilities that import the engine directly.

These are NOT product components. They touch only the ``engine`` seam (no store, tick loop,
REST/WS API, or persistence) and exist to eyeball the simulation during development. The real,
WS-streamed browser canvas with act/inspect/feed arrives in v0.4 under ``/web``.
"""

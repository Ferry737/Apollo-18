"""Market-data providers.

Each provider exposes ``fetch(symbol, ...) -> list[Bar]`` and a ``download``
helper that persists into the Store. Connectivity is READ-ONLY: these download
historical OHLCV; none of them ever place an order.
"""

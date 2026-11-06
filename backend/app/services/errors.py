"""Domain errors raised by services."""


class TradeError(Exception):
    """A trade or watchlist request that fails validation. Message is user-facing."""


class NotFoundError(Exception):
    """Requested entity does not exist."""

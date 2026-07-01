"""Portfolio — tracks cash, positions, and marks-to-market each bar.

Realized PnL uses proper lot accounting: when a trade reduces the position
magnitude (closing lots), we realize (fill_price - avg_cost) * lots_closed. This
makes win-rate / profit-factor meaningful and consistent with the direction the
position was held. Single-symbol in the MVP for clarity; the structure
generalises to multi-asset in Phase 4.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.enums import Side
from ..core.models import EquityPoint, Position, Trade


def _sign(side: Side) -> int:
    return 1 if side == Side.LONG else -1


@dataclass
class Portfolio:
    initial_capital: float
    positions: dict[str, Position] = field(default_factory=dict)
    cash: float = 0.0
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[EquityPoint] = field(default_factory=list)
    _peak_equity: float = 0.0
    _last_equity: float = 0.0

    def __post_init__(self) -> None:
        self.cash = self.initial_capital
        self._last_equity = self.initial_capital
        self._peak_equity = self.initial_capital

    # -------------------------------------------------------------- positions
    def _ensure(self, symbol: str) -> Position:
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)
        return self.positions[symbol]

    def apply_trade(self, trade: Trade) -> None:
        """Apply a (simulated) fill: move cash, roll the position, realize PnL."""
        pos = self._ensure(trade.symbol)
        signed_qty = trade.qty * _sign(trade.side)  # + adds, - reduces holdings
        old_qty = pos.qty
        new_qty = old_qty + signed_qty

        # Realize PnL on the portion of the trade that closes existing lots.
        # A "closing" component exists when the trade direction opposes the
        # current position, or trims it toward zero.
        realized = 0.0
        if old_qty != 0:
            closing = 0.0
            if (old_qty > 0 and signed_qty < 0) or (old_qty < 0 and signed_qty > 0):
                closing = min(abs(signed_qty), abs(old_qty)) * (1 if old_qty > 0 else -1)
            if closing != 0:
                # closing>0 means we held long and sold; closing<0 means short cover
                direction = 1 if old_qty > 0 else -1
                realized = direction * closing * (trade.price - pos.avg_price)
        trade.realized_pnl = realized

        # Cash impact: buying spends cash, selling adds cash (net of fees).
        notional = trade.notional
        if trade.side == Side.LONG:
            self.cash -= notional + trade.fee
        else:
            self.cash += notional - trade.fee

        # Roll weighted-average cost. When the position flips sign, the
        # remaining inventory is repriced at the fill (new lot).
        if new_qty == 0:
            pos.avg_price = 0.0
        elif (old_qty == 0) or ((old_qty > 0) == (new_qty > 0) and abs(new_qty) > abs(old_qty)):
            # opening or adding in the same direction
            pos.avg_price = (abs(old_qty) * pos.avg_price + abs(signed_qty) * trade.price) / abs(new_qty)
        elif (old_qty > 0) != (new_qty > 0):
            # flipped through zero -> remainder is a fresh lot at fill price
            pos.avg_price = trade.price
        # else: pure trim, avg_price unchanged

        pos.qty = new_qty
        self.trades.append(trade)

    # ------------------------------------------------------------- valuation
    def mark_to_market(self, symbol: str, price: float, ts: object) -> float:
        """Revalue positions at the latest price and record the equity point."""
        positions_value = 0.0
        for sym, pos in self.positions.items():
            px = price if sym == symbol else 0.0  # MVP: single priced symbol
            positions_value += pos.qty * px
        equity = self.cash + positions_value
        self._last_equity = equity
        self._peak_equity = max(self._peak_equity, equity)
        self.equity_curve.append(
            EquityPoint(
                ts=ts,  # type: ignore[arg-type]
                equity=equity,
                cash=self.cash,
                positions_value=positions_value,
            )
        )
        return equity

    @property
    def equity(self) -> float:
        return self._last_equity

    @property
    def drawdown_from_peak_pct(self) -> float:
        """Current drawdown from peak equity, as a percent (>=0)."""
        if self._peak_equity <= 0:
            return 0.0
        return max(0.0, (self._peak_equity - self._last_equity) / self._peak_equity * 100.0)

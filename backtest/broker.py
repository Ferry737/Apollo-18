"""Simulated broker — turns target weights into fills with fees + slippage.

The engine asks the broker to move the portfolio from its current weight in the
symbol toward the strategy's target weight. The broker computes the delta in
shares, applies slippage to the fill price, and charges a fee in basis points.

This is the PAPER-ONLY execution surface: it never touches a real exchange.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.enums import Side
from ..core.models import Bar, Trade
from .portfolio import Portfolio


@dataclass
class SimulatedBroker:
    fee_bps: float = 5.0       # per-fill fee as a fraction (0.05%)
    slippage_bps: float = 2.0  # adverse fill slippage (0.02%)
    # Minimum change in target weight required to trade. Prevents churning on
    # boundary toggles: a strategy flipping between 0 and 1 every bar would
    # otherwise incur a fee on every bar. 0.05 = 5% of capital.
    min_trade_weight: float = 0.05

    def rebalance(
        self, symbol: str, target_weight: float, bar: Bar, portfolio: Portfolio
    ) -> Trade | None:
        """Trade toward ``target_weight``; return the fill, or None if no trade.

        Fills happen at the bar's close, slipped adversely in the trade
        direction. Fees are charged on the notional. A deadband
        (``min_trade_weight``) suppresses uneconomic churn.
        """
        price = bar.close
        equity = portfolio.equity
        if equity <= 0 or price <= 0:
            return None

        pos = portfolio.positions.get(symbol)
        current_qty = pos.qty if pos else 0.0
        current_weight = (current_qty * price) / equity
        delta_weight = target_weight - current_weight
        # Suppress churn: only transact if the weight change is meaningful.
        if abs(delta_weight) < self.min_trade_weight:
            return None

        target_qty = target_weight * equity / price
        trade_qty = target_qty - current_qty
        if abs(trade_qty) < 1e-9:
            return None

        side = Side.LONG if trade_qty > 0 else Side.SHORT
        signed_qty = abs(trade_qty)
        slip = self.slippage_bps / 1e4
        fill_price = price * (1 + slip) if side == Side.LONG else price * (1 - slip)
        notional = signed_qty * fill_price
        fee = notional * (self.fee_bps / 1e4)

        trade = Trade(
            ts=bar.ts,
            symbol=symbol,
            side=side,
            qty=signed_qty,
            price=fill_price,
            fee=fee,
            slippage=abs(fill_price - price),
        )
        portfolio.apply_trade(trade)
        return trade

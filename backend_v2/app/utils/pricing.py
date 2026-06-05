"""
Pricing calculation utilities
"""
from typing import List, Dict, Any


class PricingCalculator:
    """
    Handles custom pricing calculations for parts.

    Calculates:
    - Local price (base price * forex rate)
    - Markup price (base price * (1 + markup))
    - Local markup price (markup price * forex rate) - FINAL PRICE
    """

    @staticmethod
    def calculate_prices(
        base_price: float,
        forex_rate: float,
        markup: float,
        base_currency: str = "USD",
        local_currency: str = "MYR"
    ) -> Dict[str, float]:
        """
        Calculate all price variants for a part.

        Args:
            base_price: Original price in base currency
            forex_rate: Exchange rate to local currency
            markup: Markup percentage (0.2 = 20%)
            base_currency: Base currency code (default: USD)
            local_currency: Local currency code (default: MYR)

        Returns:
            Dictionary with calculated prices
        """
        local_price = round(base_price * forex_rate, 2)
        markup_price = round(base_price * (1 + markup), 2)
        local_markup_price = round(markup_price * forex_rate, 2)

        return {
            "price": base_price,
            "localPrice": local_price,
            "markupPrice": markup_price,
            "localMarkupPrice": local_markup_price,
            "currency": base_currency,
            "localCurrency": local_currency
        }

    @staticmethod
    def apply_pricing_to_parts(
        parts: List[Dict[str, Any]],
        forex_rate: float,
        markup: float,
        local_currency: str = "MYR"
    ) -> List[Dict[str, Any]]:
        """
        Apply pricing to a list of parts in-place.

        Args:
            parts: List of part dictionaries
            forex_rate: Exchange rate to local currency
            markup: Markup percentage
            local_currency: Local currency code

        Returns:
            Modified list of parts with pricing fields added
        """
        for part in parts:
            # Handle ObjectId to string conversion
            if "_id" in part:
                part["_id"] = str(part["_id"])

            base_price = part.get("price", 0)
            base_currency = part.get("currency", "USD")

            prices = PricingCalculator.calculate_prices(
                base_price=base_price,
                forex_rate=forex_rate,
                markup=markup,
                base_currency=base_currency,
                local_currency=local_currency
            )

            # Update part with calculated prices
            part.update(prices)

        return parts

"""
AliExpress parsing tests on a REAL saved search page (24 Sep 2026, Pakistan storefront, PKR).

How to run from the engine/ folder:
    python -m unittest tests.test_aliexpress -v
"""

import asyncio
import os
import unittest

try:
    from scrapling.parser import Selector
except ImportError:
    from scrapling.parser import Adaptor as Selector

from app.engine.analyze import opportunity
from app.listing import SELL, SUPPLY, Listing
from app.sources.aliexpress import cost_query, pack_qty, parse_search_page


# ---------------------------------------------------------------------------
# Path to the real saved HTML fixture
# ---------------------------------------------------------------------------
FIXTURE = os.path.join(
    os.path.dirname(__file__),
    "fixtures",
    "search",
    "aliexpress_silicone_baking_mat.html",
)


# ===========================================================================
# 1. Tests on a REAL saved AliExpress search page
# ===========================================================================
@unittest.skipUnless(
    os.path.isfile(FIXTURE),
    "Save the real page to tests/fixtures/search/aliexpress_silicone_baking_mat.html",
)
class TestRealSearchPage(unittest.TestCase):
    """
    These tests load a real AliExpress HTML page that was saved earlier
    and check that parse_search_page() extracts the correct data.
    """

    @classmethod
    def setUpClass(cls):
        # Load the saved HTML once and parse all cards into a dictionary
        # keyed by source_id (item ID)
        with open(FIXTURE, encoding="utf-8", errors="ignore") as f:
            cls.rows = {
                l.source_id: l
                for l in parse_search_page(Selector(f.read()), 50)
            }

    def test_every_card_is_parsed_including_bundle_ads(self):
        """
        Make sure we parse a decent number of cards
        and that even special 'bundle deal' ad cards are included.
        """
        self.assertGreaterEqual(len(self.rows), 12)
        self.assertIn("1005010572710729", self.rows)  # known bundle-deal ad

    def test_new_shopper_price_is_not_the_cost(self):
        """
        When AliExpress shows a special 'new shopper' price,
        we must use the higher regular price as the real cost.
        """
        l = self.rows["1005009695806453"]  # Rs.1,572 new-shopper / Rs.3,150 regular
        self.assertAlmostEqual(l.raw["shown_price"], 5.66, places=2)
        self.assertAlmostEqual(l.price, 11.34, places=2)          # ← we take the higher one
        self.assertTrue(l.raw["new_shopper_price"])
        self.assertTrue(l.raw["price_crosscheck"])                # matches data in the link

    def test_free_shipping_threshold_is_not_a_price(self):
        """
        'Free shipping over Rs.3,154' must NOT be treated as the product price.
        """
        l = self.rows["1005009548245425"]
        self.assertAlmostEqual(l.price, 5.09, places=2)
        self.assertIsNone(l.raw["original_price"])
        self.assertFalse(l.raw["new_shopper_price"])
        self.assertIsNone(l.shipping_cost)                        # shipping still unknown
        self.assertAlmostEqual(l.raw["free_shipping_over"], 11.35, places=2)

    def test_plain_discount_uses_shown_price(self):
        """
        Normal discounts (no new-shopper / bundle condition)
        should use the shown (sale) price.
        """
        l = self.rows["1005008924526507"]  # -52% normal discount
        self.assertAlmostEqual(l.price, 5.57, places=2)

    def test_rating_and_sold(self):
        """
        Rating and sold-count must be extracted correctly.
        """
        l = self.rows["1005006669112295"]
        self.assertEqual((l.rating, l.sold_count), (4.8, 10000))

    def test_no_card_cost_is_below_its_shown_price(self):
        """
        Safety check: the final cost we store should never be
        lower than the price that was actually shown on the card.
        """
        for l in self.rows.values():
            self.assertGreaterEqual(
                l.price,
                l.raw["shown_price"],
                msg=f"Bad cost for item {l.source_id}",
            )

    # ------------------------------------------------------------------
    # Extra real-data checks for supplier details
    # ------------------------------------------------------------------

    def test_every_listing_has_required_fields(self):
        """
        Every parsed card must have the core supplier fields filled.
        """
        for sid, l in self.rows.items():
            with self.subTest(source_id=sid):
                self.assertEqual(l.source, "aliexpress")
                self.assertEqual(l.side, SUPPLY)
                self.assertTrue(l.source_id)
                self.assertTrue(l.title and len(l.title) >= 5)
                self.assertTrue(l.url.startswith("https://www.aliexpress.com/item/"))
                self.assertIn(l.source_id, l.url)
                self.assertIsInstance(l.price, float)
                self.assertGreater(l.price, 0)
                self.assertIsInstance(l.confidence, float)
                self.assertGreaterEqual(l.confidence, 0.4)
                self.assertLessEqual(l.confidence, 0.95)

    def test_image_url_is_present_and_valid(self):
        """
        Most cards should have an image URL (http/https).
        """
        with_image = [l for l in self.rows.values() if l.image_url]
        self.assertGreaterEqual(len(with_image), 8, "Too few cards have images")

        for l in with_image:
            with self.subTest(source_id=l.source_id):
                self.assertTrue(
                    l.image_url.startswith("http://") or l.image_url.startswith("https://"),
                    f"Bad image_url: {l.image_url}",
                )

    def test_confidence_score_is_reasonable(self):
        """
        Confidence should be higher when rating + sold count exist.
        """
        for l in self.rows.values():
            with self.subTest(source_id=l.source_id):
                self.assertGreaterEqual(l.confidence, 0.40)
                self.assertLessEqual(l.confidence, 0.95)

                # Cards that have both rating and sold should score higher
                if l.rating and l.sold_count:
                    self.assertGreaterEqual(l.confidence, 0.70)

    def test_shipping_cost_and_free_over(self):
        """
        Check shipping-related fields on real cards.
        """
        # At least one card should have free_shipping_over recorded
        free_over_cards = [
            l for l in self.rows.values()
            if l.raw.get("free_shipping_over") is not None
        ]
        self.assertGreaterEqual(len(free_over_cards), 1)

        for l in free_over_cards:
            with self.subTest(source_id=l.source_id):
                self.assertIsInstance(l.raw["free_shipping_over"], float)
                self.assertGreater(l.raw["free_shipping_over"], 0)

        # shipping_cost is either None, 0.0, or a positive float
        for l in self.rows.values():
            with self.subTest(source_id=l.source_id):
                if l.shipping_cost is not None:
                    self.assertIsInstance(l.shipping_cost, float)
                    self.assertGreaterEqual(l.shipping_cost, 0.0)

    def test_raw_metadata_is_consistent(self):
        """
        raw dict must contain the expected keys and stay consistent with the main fields.
        """
        required_raw_keys = {
            "shown_price",
            "original_price",
            "new_shopper_price",
            "bundle_deal",
            "cost_basis",
            "free_shipping_over",
            "price_crosscheck",
            "pack_qty",
            "ad",
        }

        for sid, l in self.rows.items():
            with self.subTest(source_id=sid):
                for key in required_raw_keys:
                    self.assertIn(key, l.raw, f"Missing raw key: {key}")

                # shown_price must exist and be <= final price
                self.assertIsInstance(l.raw["shown_price"], float)
                self.assertGreaterEqual(l.price, l.raw["shown_price"])

                # pack_qty must be a positive integer
                self.assertIsInstance(l.raw["pack_qty"], int)
                self.assertGreaterEqual(l.raw["pack_qty"], 1)

    def test_specific_known_products(self):
        """
        Spot-check a few known real products from the fixture
        for title, price range and basic quality signals.
        """
        # Example 1 – high sold count product
        l = self.rows.get("1005006669112295")
        self.assertIsNotNone(l)
        self.assertIn("silicone", l.title.lower())
        self.assertEqual(l.rating, 4.8)
        self.assertEqual(l.sold_count, 10000)
        self.assertGreater(l.confidence, 0.75)

        # Example 2 – new shopper card
        l = self.rows.get("1005009695806453")
        self.assertIsNotNone(l)
        self.assertTrue(len(l.title) > 10)
        self.assertTrue(l.raw["new_shopper_price"])

        # Example 3 – free shipping over threshold
        l = self.rows.get("1005009548245425")
        self.assertIsNotNone(l)
        self.assertAlmostEqual(l.raw["free_shipping_over"], 11.35, places=2)


# ===========================================================================
# 2. Unit tests for helper functions (pack_qty + cost_query)
# ===========================================================================
class TestPackAndQuery(unittest.TestCase):
    """
    Pure unit tests – no HTML needed.
    Checks that we correctly detect pack size and clean Amazon titles.
    """

    def test_pack_qty(self):
        """Extract number of units from product titles."""
        self.assertEqual(pack_qty("NiHome 4-Pack Reusable Silicone Bread Sling"), 4)
        self.assertEqual(pack_qty("Koolstuffs Silicone Baking Mat, 3 Pack"), 3)
        self.assertEqual(pack_qty("Set of 2 mats"), 2)
        self.assertEqual(pack_qty("1/2PCS Fiber-Free Silicone Bread Sling"), 1)
        self.assertEqual(pack_qty("Silicone baking mat 30x40cm"), 1)

    def test_cost_query_drops_brand_and_keeps_pack_size(self):
        """
        cost_query should:
        - remove brand names
        - keep the important product words
        - append pack size when > 1
        """
        self.assertEqual(
            cost_query("Koolstuffs Silicone Baking Mat, Nonstick and Reusable, 3 Pack"),
            "silicone baking mat 3pcs",
        )

        q = cost_query("HOTEC Silicone Baking Mats 3 Pack – Non-Stick Reusable")
        self.assertNotIn("hotec", q)
        self.assertTrue(q.startswith("silicone baking mats") and q.endswith("3pcs"), q)

        self.assertEqual(
            cost_query("Silicone Baking Mat Set of 6, Easy Clean & Non-Stick Food Grade"),
            "silicone baking mat 6pcs",
        )

    def test_cost_query_strips_whole_brands(self):
        """Amazon Basics / house brands must be completely removed."""
        self.assertEqual(
            cost_query("Amazon Basics Silicone Rectangular Baking Mat, Non-Stick, Reusable"),
            "silicone rectangular baking mat",
        )
        self.assertNotIn(
            "basics",
            cost_query("Amazon Basics Silicone Baking Mat for Macarons"),
        )


# ===========================================================================
# 3. Integration tests – does the analyze engine use the cost correctly?
# ===========================================================================
class TestAnalyzeUsesComparableCost(unittest.TestCase):
    """
    These tests check that the opportunity() function
    correctly scales supplier cost by pack size and handles
    missing shipping information.
    """

    def _sell(self, title, price):
        """Helper: create a fake Amazon (SELL) listing."""
        return Listing(
            source="amazon",
            side=SELL,
            source_id="B0TEST",
            title=title,
            url="u",
            price=price,
            rating=4.7,
        )

    def test_pack_size_scales_supplier_cost_and_is_disclosed(self):
        """
        If Amazon sells a 4-pack and AliExpress sells single units,
        the engine must multiply the supplier price by 4.
        """
        sell = self._sell(
            "NiHome 4-Pack Reusable Silicone Bread Sling for Dutch Oven", 13.96
        )
        sup = Listing(
            source="aliexpress",
            side=SUPPLY,
            source_id="1",
            title="Reusable Silicone Bread Sling for Dutch Oven",
            url="u",
            price=3.98,
            shipping_cost=0.0,
            raw={"pack_qty": 1, "cost_basis": "shown"},
        )

        o = asyncio.run(opportunity(sell, [sup], "kitchen", {}))

        # 3.98 × 4 = 15.92
        self.assertAlmostEqual(o["inputs"]["supplier"], 15.92, places=2)
        self.assertTrue(any("× 4" in a for a in o["assumptions"]))

    def test_unknown_shipping_is_labelled_as_estimate(self):
        """
        When shipping cost is missing, the engine should
        mark it as an estimate and add a clear assumption.
        """
        sell = self._sell("Silicone Baking Mat Sheet Reusable", 29.99)
        sup = Listing(
            source="aliexpress",
            side=SUPPLY,
            source_id="2",
            title="Silicone Baking Mat Sheet Reusable Non-Stick",
            url="u",
            price=5.09,
            shipping_cost=None,
            raw={"pack_qty": 1, "free_shipping_over": 11.35},
        )

        o = asyncio.run(opportunity(sell, [sup], "kitchen", {}))

        ship = next(l for l in o["profit"]["lines"] if l["key"] == "ship")
        self.assertIn("estimate", ship["label"])
        self.assertTrue(any("Shipping isn't shown" in a for a in o["assumptions"]))


# ---------------------------------------------------------------------------
# Allow running the file directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main()
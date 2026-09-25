"""
AliExpress parsing tests on a REAL saved search page (24 Sep 2026, Pakistan storefront, PKR).
Run from engine/:   python -m unittest tests.test_aliexpress -v
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

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "search", "aliexpress_silicone_baking_mat.html")


@unittest.skipUnless(os.path.isfile(FIXTURE), "save the real page to tests/fixtures/search/aliexpress_silicone_baking_mat.html")
class TestRealSearchPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE, encoding="utf-8", errors="ignore") as f:
            cls.rows = {l.source_id: l for l in parse_search_page(Selector(f.read()), 50)}

    def test_every_card_is_parsed_including_bundle_ads(self):
        self.assertGreaterEqual(len(self.rows), 12)
        self.assertIn("1005010572710729", self.rows)          # bundle-deal ad card (different link format)

    def test_new_shopper_price_is_not_the_cost(self):
        l = self.rows["1005009695806453"]                    # Rs.1,572.07 new-shopper, Rs.3,150.45 regular
        self.assertAlmostEqual(l.raw["shown_price"], 5.66, places=2)
        self.assertAlmostEqual(l.price, 11.34, places=2)
        self.assertTrue(l.raw["new_shopper_price"])
        self.assertTrue(l.raw["price_crosscheck"])            # matches the price data in the link

    def test_free_shipping_threshold_is_not_a_price(self):
        l = self.rows["1005009548245425"]                    # Rs.1,412.9, no discount, "Free shipping over Rs.3,154"
        self.assertAlmostEqual(l.price, 5.09, places=2)
        self.assertIsNone(l.raw["original_price"])
        self.assertFalse(l.raw["new_shopper_price"])
        self.assertIsNone(l.shipping_cost)                    # shipping for one unit is unknown
        self.assertAlmostEqual(l.raw["free_shipping_over"], 11.35, places=2)

    def test_plain_discount_uses_shown_price(self):
        l = self.rows["1005008924526507"]                    # -52% with no new-shopper / bundle condition
        self.assertAlmostEqual(l.price, 5.57, places=2)

    def test_rating_and_sold(self):
        l = self.rows["1005006669112295"]
        self.assertEqual((l.rating, l.sold_count), (4.8, 10000))

    def test_no_card_cost_is_below_its_shown_price(self):
        for l in self.rows.values():
            self.assertGreaterEqual(l.price, l.raw["shown_price"], l.source_id)


class TestPackAndQuery(unittest.TestCase):
    def test_pack_qty(self):
        self.assertEqual(pack_qty("NiHome 4-Pack Reusable Silicone Bread Sling"), 4)
        self.assertEqual(pack_qty("Koolstuffs Silicone Baking Mat, 3 Pack"), 3)
        self.assertEqual(pack_qty("Set of 2 mats"), 2)
        self.assertEqual(pack_qty("1/2PCS Fiber-Free Silicone Bread Sling"), 1)
        self.assertEqual(pack_qty("Silicone baking mat 30x40cm"), 1)

    def test_cost_query_drops_brand_and_keeps_pack_size(self):
        self.assertEqual(cost_query("Koolstuffs Silicone Baking Mat, Nonstick and Reusable, 3 Pack"), "silicone baking mat 3pcs")
        q = cost_query("HOTEC Silicone Baking Mats 3 Pack – Non-Stick Reusable")
        self.assertNotIn("hotec", q)
        self.assertTrue(q.startswith("silicone baking mats") and q.endswith("3pcs"), q)
        self.assertEqual(cost_query("Silicone Baking Mat Set of 6, Easy Clean & Non-Stick Food Grade"), "silicone baking mat 6pcs")

    def test_cost_query_strips_whole_brands(self):
        self.assertEqual(cost_query("Amazon Basics Silicone Rectangular Baking Mat, Non-Stick, Reusable"), "silicone rectangular baking mat")
        self.assertNotIn("basics", cost_query("Amazon Basics Silicone Baking Mat for Macarons"))


class TestAnalyzeUsesComparableCost(unittest.TestCase):
    def _sell(self, title, price):
        return Listing(source="amazon", side=SELL, source_id="B0TEST", title=title, url="u", price=price, rating=4.7)

    def test_pack_size_scales_supplier_cost_and_is_disclosed(self):
        sell = self._sell("NiHome 4-Pack Reusable Silicone Bread Sling for Dutch Oven", 13.96)
        sup = Listing(source="aliexpress", side=SUPPLY, source_id="1", title="Reusable Silicone Bread Sling for Dutch Oven",
                      url="u", price=3.98, shipping_cost=0.0, raw={"pack_qty": 1, "cost_basis": "shown"})
        o = asyncio.run(opportunity(sell, [sup], "kitchen", {}))
        self.assertAlmostEqual(o["inputs"]["supplier"], 15.92, places=2)          # 3.98 x 4
        self.assertTrue(any("× 4" in a for a in o["assumptions"]))

    def test_unknown_shipping_is_labelled_as_estimate(self):
        sell = self._sell("Silicone Baking Mat Sheet Reusable", 29.99)
        sup = Listing(source="aliexpress", side=SUPPLY, source_id="2", title="Silicone Baking Mat Sheet Reusable Non-Stick",
                      url="u", price=5.09, shipping_cost=None, raw={"pack_qty": 1, "free_shipping_over": 11.35})
        o = asyncio.run(opportunity(sell, [sup], "kitchen", {}))
        ship = next(l for l in o["profit"]["lines"] if l["key"] == "ship")
        self.assertIn("estimate", ship["label"])
        self.assertTrue(any("Shipping isn't shown" in a for a in o["assumptions"]))


if __name__ == "__main__":
    unittest.main()

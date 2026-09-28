"""
Comprehensive Unit Tests for Entity Extraction & Multi-Signal Product Matching.
Tests:
- Entity & spec extraction from noisy marketplace titles
- Pack size extraction
- Material and dimension resolution
- Multi-signal matching score accuracy & immunity to generic word traps
- Price sanity / teaser protection
"""
from __future__ import annotations

import unittest

from app.engine.entity import extract_entity, extract_material, extract_pack_qty, extract_dimensions
from app.engine.matching import best, score
from app.listing import SELL, SUPPLY, Listing


class TestEntityExtraction(unittest.TestCase):

    def test_extract_pack_qty(self):
        self.assertEqual(extract_pack_qty("Silicone Baking Mat 2 Pack"), 2)
        self.assertEqual(extract_pack_qty("Set of 4 Reusable Dutch Oven Bread Mats"), 4)
        self.assertEqual(extract_pack_qty("12-Piece Kitchen Utensil Set"), 12)
        self.assertEqual(extract_pack_qty("Stainless Steel Water Bottle 32oz"), 1)
        self.assertEqual(extract_pack_qty("5 in 1 Hair Styler"), 5)

    def test_extract_material(self):
        self.assertEqual(extract_material("Premium Silicone Baking Mat"), "silicone")
        self.assertEqual(extract_material("Heavy Duty Stainless Steel Spatula"), "stainless steel")
        self.assertEqual(extract_material("Organic Bamboo Cutting Board"), "bamboo")
        self.assertEqual(extract_material("Cast Iron Skillet Pan 10-inch"), "cast iron")
        self.assertIsNone(extract_material("Smart LED Desk Lamp"))

    def test_extract_dimensions(self):
        dims = extract_dimensions("Large Silicone Baking Mat (28x20 in) for Countertop")
        self.assertTrue(any("28x20" in d for d in dims))

        dims2 = extract_dimensions("Stainless Steel Insulated Tumbler 30oz")
        self.assertTrue(any("30oz" in d for d in dims2))

    def test_canonical_entity_clean_query(self):
        e = extract_entity("Amazon Basics Silicone Macaron Baking Mat Sheet, Set of 2")
        self.assertEqual(e.pack_qty, 2)
        self.assertEqual(e.material, "silicone")
        self.assertNotIn("basics", e.canonical_query)
        self.assertIn("silicone", e.canonical_query)
        self.assertIn("baking mat", e.canonical_query)
        self.assertTrue(e.canonical_query.endswith("2pcs"))


class TestMultiSignalMatching(unittest.TestCase):

    def _sell(self, title: str, price: float = 24.99) -> Listing:
        return Listing(source="amazon", side=SELL, source_id="B0TEST", title=title, url="http://amazon/dp/1", price=price)

    def _sup(self, title: str, price: float = 6.50, shipping: float = 0.0) -> Listing:
        return Listing(
            source="aliexpress",
            side=SUPPLY,
            source_id="1005001",
            title=title,
            url="http://aliexpress/item/1.html",
            price=price,
            shipping_cost=shipping,
            rating=4.8,
            sold_count=5000,
        )

    def test_matching_same_product_with_different_seo_titles(self):
        """Amazon SEO title vs AliExpress Chinese-translated title for the same physical product."""
        amazon = self._sell("Large Silicone Pastry Mat with Measurements, Non-Stick Baking Mat Counter Sheet (28x20 in)")
        ali = self._sup("Kitchen Dough Pad Baking Tool Silicone Kneading Dough Mat Scale Non-Stick Large Sheet 60x40cm")

        match_score = score(amazon, ali)
        # Should achieve high confidence match despite different title structures
        self.assertGreaterEqual(match_score, 0.55)

    def test_penalty_for_different_products_sharing_generic_words(self):
        """A silicone spatula must NOT match a silicone baking mat even if sharing 'silicone', 'kitchen', 'heat resistant'."""
        amazon_mat = self._sell("Silicone Baking Mat Non-Stick Heat Resistant Kitchen Countertop Liner")
        ali_spatula = self._sup("Silicone Spatula Heat Resistant Kitchen Non-Stick Cooking Scraper Tool")

        mat_vs_spatula = score(amazon_mat, ali_spatula)
        
        # Proper mat vs mat match for comparison
        ali_mat = self._sup("Non-Stick Silicone Baking Mat Oven Sheet Liner Kitchen Pastry Pad")
        mat_vs_mat = score(amazon_mat, ali_mat)

        self.assertLess(mat_vs_spatula, 0.45)
        self.assertGreater(mat_vs_mat, 0.65)
        self.assertGreater(mat_vs_mat, mat_vs_spatula + 0.20)

    def test_material_mismatch_penalty(self):
        """Wooden utensils should not match Stainless Steel utensils."""
        amazon_steel = self._sell("Stainless Steel Kitchen Cooking Utensil Spoon")
        ali_wood = self._sup("Natural Wooden Cooking Spoon Kitchen Utensil")

        s = score(amazon_steel, ali_wood)
        self.assertLess(s, 0.40)

    def test_price_sanity_safeguards(self):
        """Extremely low teaser prices (e.g. $0.20 on a $25 item) or overpriced resellers should be penalized."""
        amazon = self._sell("Premium Stainless Steel Chef Knife 8 inch", price=45.00)
        
        # Teaser / sample listing (e.g. $0.50 knife sheath or sticker)
        teaser_sup = self._sup("Stainless Steel Knife Accessory", price=0.50)
        # Legitimate wholesale supplier ($12.00)
        real_sup = self._sup("8 inch Stainless Steel Kitchen Chef Knife Professional", price=12.00)
        # Overpriced dropship reseller ($42.00)
        reseller_sup = self._sup("8 inch Stainless Steel Kitchen Chef Knife", price=42.00)

        s_teaser = score(amazon, teaser_sup)
        s_real = score(amazon, real_sup)
        s_reseller = score(amazon, reseller_sup)

        self.assertGreater(s_real, s_teaser)
        self.assertGreater(s_real, s_reseller)

    def test_best_selection_chooses_most_accurate_supplier(self):
        amazon = self._sell("Silicone Macaron Baking Mat Set of 2 Non-Stick Oven Liner", price=18.99)

        candidates = [
            self._sup("Silicone Spatula Spoon Kitchen Tool", price=2.00), # wrong product
            self._sup("Silicone Baking Mat Macaron Pastry Sheet Non-Stick", price=3.50), # correct product
            self._sup("Silicone Baking Mat Sheet Cheap", price=0.10), # teaser accessory
        ]

        pick, pick_score = best(amazon, candidates)
        self.assertIsNotNone(pick)
        self.assertIn("Macaron", pick.title)
        self.assertGreaterEqual(pick_score, 0.55)

    def test_price_safeguard_is_pack_size_normalized(self):
        """
        A supplier listing priced for its own bulk lot must not be judged against the sell
        listing's raw price — that used to compare a 10-pack's total price directly against a
        2-pack's retail price, wrongly flagging a perfectly good bulk-lot match as an
        overpriced 'reseller' (or the reverse: wrongly favoring a mismatched pack size that
        merely looked cheap per-listing).
        """
        sell = self._sell("No Pull Dog Harness Reflective Adjustable, 2 Pack", price=25.99)
        bulk_10pack = self._sup("No Pull Dog Harness Reflective Adjustable 10 Pack", price=28.00, shipping=1.50)
        # Per-2-unit cost is ~$5.60 + $1.50 ship — squarely inside the normal wholesale band,
        # nowhere near the raw $28 that would trigger the reseller flag unscaled.
        s = score(sell, bulk_10pack)
        self.assertGreater(s, 0.55)

    def test_head_noun_fallback_catches_mismatch_outside_curated_clusters(self):
        """
        NOUN_CLUSTERS can't enumerate every category. Before the head-noun fallback, two
        completely different products with no cluster hit on either side scored a neutral 1.0
        cluster_score — zero protection. A jump rope vs. a kitchen scale is exactly that case:
        neither 'rope' nor 'scale' is a curated cluster.
        """
        sell = self._sell("Weighted Jump Rope Cordless Counter", price=21.99)
        wrong = self._sup("Digital Kitchen Food Scale Counter", price=4.50)
        right = self._sup("Cordless Jump Rope Digital Counter", price=4.20)

        s_wrong = score(sell, wrong)
        s_right = score(sell, right)
        self.assertLess(s_wrong, 0.45)
        self.assertGreater(s_right, s_wrong + 0.30)


if __name__ == "__main__":
    unittest.main()

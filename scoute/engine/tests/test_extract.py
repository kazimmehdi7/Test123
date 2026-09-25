"""
Price extraction tests. Run from engine/:   python -m unittest tests.test_extract -v

Any real pages you save in tests/fixtures/*.html are also checked (a price must be
found and be usable, or the page must be recognised as unavailable).
"""
import asyncio
import glob
import os
import unittest
from unittest import mock

try:
    from scrapling.parser import Selector
except ImportError:  # older Scrapling
    from scrapling.parser import Adaptor as Selector

from app.extract import LIKELY, NONE, UNAVAILABLE, UNVERIFIED, VERIFIED, ai_check, extract_card_price, extract_price
from app.extract.common import Candidate, MethodResult, money_in_text, parse_money


def page(html):
    return Selector(html)


def run(coro):
    return asyncio.run(coro)


PRODUCT = """<html><head>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product","name":"Mat",
 "offers":{"@type":"Offer","price":"19.99","priceCurrency":"USD"}}</script></head><body>
<div id="corePrice_feature_div">
  <span class="a-price"><span class="a-offscreen">$19.99</span></span>
  <span class="a-price a-text-price"><span class="a-offscreen">$29.99</span></span>
  <span>List Price: $29.99</span>
  <span>($0.50 / Count)</span>
</div>
<div id="buybox"><span>FREE delivery $5.99 shipping</span><input id="add-to-cart-button"></div>
</body></html>"""

CONFLICT = """<html><head><script type="application/ld+json">{"@type":"Product","offers":{"price":"9.99","priceCurrency":"USD"}}</script></head>
<body><div id="corePrice_feature_div"><span class="a-price"><span class="a-offscreen">$24.99</span></span></div></body></html>"""


class TestMoney(unittest.TestCase):
    def test_needs_currency(self):
        self.assertIsNone(parse_money("19.99"))
        self.assertEqual(parse_money("$1,299.99").value, 1299.99)

    def test_pkr_is_converted(self):
        self.assertAlmostEqual(parse_money("PKR 5,555").value, 20.0, places=1)

    def test_skips_list_unit_shipping_prices(self):
        vals = [c.value for c in money_in_text("List Price: $29.99  $19.99  ($0.50 / Count)  $5.99 shipping  Save $10.00")]
        self.assertEqual(vals, [19.99])

    def test_absurd_prices_rejected(self):
        self.assertIsNone(parse_money("$0.01"))
        self.assertIsNone(parse_money("$99999"))


class TestProductVote(unittest.TestCase):
    def test_structured_and_selectors_agree(self):
        r = run(extract_price(page(PRODUCT), "amazon", use_ai=False))
        self.assertEqual(r.status, VERIFIED)
        self.assertEqual(r.price, 19.99)
        self.assertIn("structured", r.agreeing)
        self.assertIn("selectors", r.agreeing)

    def test_strike_through_price_never_wins(self):
        r = run(extract_price(page(PRODUCT), "amazon", use_ai=False))
        self.assertNotEqual(r.price, 29.99)

    def test_split_price(self):
        html = """<div id="corePrice_feature_div"><span class="a-price"><span class="a-price-symbol">$</span>
                  <span class="a-price-whole">14.</span><span class="a-price-fraction">99</span></span></div>"""
        r = run(extract_price(page(html), "amazon", use_ai=False))
        self.assertEqual(r.price, 14.99)
        self.assertTrue(r.usable)

    def test_conflict_is_not_used(self):
        r = run(extract_price(page(CONFLICT), "amazon", use_ai=False))
        self.assertEqual(r.status, UNVERIFIED)
        self.assertIsNone(r.price)
        self.assertFalse(r.usable)

    def test_unavailable(self):
        r = run(extract_price(page('<div id="availability"><span>Currently unavailable.</span></div>'), "amazon", use_ai=False))
        self.assertEqual(r.status, UNAVAILABLE)
        self.assertFalse(r.usable)

    def test_empty_page(self):
        r = run(extract_price(page("<html><body>nothing</body></html>"), "amazon", use_ai=False))
        self.assertEqual(r.status, NONE)

    def test_bad_json_ld_does_not_crash(self):
        html = PRODUCT.replace('{"@context"', '{broken json "@context"')
        r = run(extract_price(page(html), "amazon", use_ai=False))
        self.assertTrue(r.usable)
        self.assertEqual(r.price, 19.99)

    def test_hidden_input_counts_as_structured(self):
        html = """<input id="attach-base-product-price" value="12.49">
                  <div id="corePrice_feature_div"><span class="a-price"><span class="a-offscreen">$12.49</span></span></div>"""
        r = run(extract_price(page(html), "amazon", use_ai=False))
        self.assertEqual((r.status, r.price), (VERIFIED, 12.49))

class TestCurrencyFromRealAmazon(unittest.TestCase):
    """Real case, 24 Sep 2026: Amazon served PKR to a Pakistani IP. The hidden price input holds
    4392.43 with no symbol; the visible price says 'PKR 4,392.43'. Both must read as $15.81."""
    PKR_PAGE = """<html><body><input id="attach-base-product-price" value="4392.43">
      <div class="twister-plus-buying-options-price-data">[{"priceAmount":4392.43,"currencySymbol":"PKR"}]</div>
      <div id="corePrice_feature_div"><span class="a-price"><span class="a-offscreen">PKR 4,392.43</span></span></div>
      </body></html>"""

    def test_symbol_less_values_use_page_currency(self):
        r = run(extract_price(page(self.PKR_PAGE), "amazon", use_ai=False))
        self.assertEqual(r.status, VERIFIED, r.summary())
        self.assertAlmostEqual(r.price, 15.81, places=2)

    def test_usd_page_unchanged(self):
        html = self.PKR_PAGE.replace("4392.43", "15.81").replace("PKR 4,392.43", "$15.81").replace('"PKR"', '"$"')
        r = run(extract_price(page(html), "amazon", use_ai=False))
        self.assertEqual((r.status, r.price), (VERIFIED, 15.81))
        

class TestCards(unittest.TestCase):
    def test_card_selector_and_pattern_agree(self):
        card = page("""<div data-asin="B0TEST"><h2><span>Mat</span></h2>
                       <span class="a-price"><span class="a-offscreen">$18.49</span></span>
                       <span class="a-price a-text-price"><span class="a-offscreen">$24.99</span></span></div>""")
        r = extract_card_price(card, "amazon", "card")
        self.assertEqual((r.status, r.price), (VERIFIED, 18.49))

    def test_card_without_price(self):
        r = extract_card_price(page("<div><h2><span>No featured offers</span></h2></div>"), "amazon", "card")
        self.assertFalse(r.usable)


class TestAiSafety(unittest.TestCase):
    OPTIONS = [Candidate(9.99, "$9.99"), Candidate(24.99, "$24.99")]

    def test_only_our_options_are_accepted(self):
        self.assertEqual(ai_check._validate({"id": 1}, self.OPTIONS).value, 24.99)
        self.assertIsNone(ai_check._validate({"id": 7}, self.OPTIONS))
        self.assertIsNone(ai_check._validate({"id": "1"}, self.OPTIONS))
        self.assertIsNone(ai_check._validate({"id": True}, self.OPTIONS))
        self.assertIsNone(ai_check._validate({"price": 0.01}, self.OPTIONS))
        self.assertIsNone(ai_check._validate("0.01", self.OPTIONS))

    def test_ai_breaks_a_tie(self):
        async def fake_ai(title, pool, zone):
            return MethodResult("ai", [c for c in pool if c.value == 24.99][:1])
        with mock.patch.object(ai_check, "extract", fake_ai):
            r = run(extract_price(page(CONFLICT), "amazon", use_ai=True))
        self.assertTrue(r.usable)
        self.assertEqual(r.price, 24.99)

    def test_ai_failure_keeps_it_unverified(self):
        async def failing_ai(title, pool, zone):
            return MethodResult("ai", [], error="HTTP 500")
        with mock.patch.object(ai_check, "extract", failing_ai):
            r = run(extract_price(page(CONFLICT), "amazon", use_ai=True))
        self.assertEqual(r.status, UNVERIFIED)
        self.assertEqual(r.methods.get("ai"), "HTTP 500")

    def test_hourly_budget(self):
        with mock.patch.object(ai_check, "MAX_PER_HOUR", 2), mock.patch.object(ai_check, "_calls", []):
            self.assertTrue(ai_check._allowed())
            self.assertTrue(ai_check._allowed())
            self.assertFalse(ai_check._allowed())


class TestSavedRealPages(unittest.TestCase):
    """Put real product pages (from engine/debug/) in tests/fixtures/ to check selectors against reality."""
    def test_fixtures(self):
        files = glob.glob(os.path.join(os.path.dirname(__file__), "fixtures", "*.html"))
        if not files:
            self.skipTest("no saved pages in tests/fixtures yet")
        for f in files:
            with self.subTest(page=os.path.basename(f)):
                site = "aliexpress" if "aliexpress" in f.lower() else "amazon"
                with open(f, encoding="utf-8", errors="ignore") as fh:
                    r = run(extract_price(Selector(fh.read()), site, use_ai=False))
                print(f"\n  {os.path.basename(f)}: {r.status} {r.price} ({r.reason})")
                self.assertIn(r.status, (VERIFIED, LIKELY, UNAVAILABLE), r.summary())


if __name__ == "__main__":
    unittest.main()

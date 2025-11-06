# agent.py
import os
import re
import time
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page
load_dotenv()
# Gemini SDK (google-genai)
from google import genai

# Setup gemini API key externally: export GEMINI_API_KEY="..."
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Set GEMINI_API_KEY environment variable for Google Gemini (google-genai).")
genai_client = genai.Client(api_key=GEMINI_API_KEY)


# ---------- Data classes ----------
@dataclass
class Product:
    title: str
    price: Optional[float]
    currency: Optional[str]
    url: str
    store: str
    extra: Dict[str, Any] = None


# ---------- Utilities ----------
def parse_price(text: Optional[str]) -> (Optional[float], Optional[str]):
    if not text:
        return None, None
    # remove thousands separators
    t = text.replace(",", "")
    m = re.search(r'([£$€])?\s*([0-9]+(?:\.[0-9]{1,2})?)', t)
    if not m:
        return None, None
    currency = m.group(1) or None
    price = float(m.group(2))
    return price, currency


# ---------- Browser controller ----------
class BrowserController:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless, args=["--disable-blink-features=AutomationControlled"])
        self.context = await self.browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36")
        return self

    async def new_page(self) -> Page:
        return await self.context.new_page()

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        finally:
            if self.playwright:
                await self.playwright.stop()


# ---------- Scrapers ----------
class StoreScraper:
    def __init__(self, page: Page):
        self.page = page

    async def search_amazon(self, query: str) -> List[Product]:
        url = "https://www.amazon.com/s?k=" + query.replace(" ", "+")
        await self.page.goto(url, timeout=60000)
        await self.page.wait_for_timeout(1500)
        html = await self.page.content()
        soup = BeautifulSoup(html, "html.parser")
        products = []
        for card in soup.select("div[data-asin]"):
            asin = card.get("data-asin")
            if not asin:
                continue
            title_tag = card.select_one("h2 a span")
            price_tag = card.select_one(".a-price .a-offscreen")
            link_tag = card.select_one("h2 a")
            title = title_tag.get_text(strip=True) if title_tag else "Unknown"
            price_text = price_tag.get_text(strip=True) if price_tag else None
            price, currency = parse_price(price_text) if price_text else (None, None)
            url = "https://www.amazon.com" + link_tag.get("href") if link_tag else url
            products.append(Product(title=title, price=price, currency=currency, url=url, store="amazon"))
        return products

    async def search_ebay(self, query: str) -> List[Product]:
        url = "https://www.ebay.com/sch/i.html?_nkw=" + query.replace(" ", "+")
        await self.page.goto(url, timeout=60000)
        await self.page.wait_for_timeout(1500)
        soup = BeautifulSoup(await self.page.content(), "html.parser")
        products = []
        for item in soup.select(".s-item"):
            title_tag = item.select_one(".s-item__title")
            price_tag = item.select_one(".s-item__price")
            link = item.select_one(".s-item__link")
            title = title_tag.get_text(strip=True) if title_tag else None
            price_text = price_tag.get_text(strip=True) if price_tag else None
            price, currency = parse_price(price_text) if price_text else (None, None)
            url = link.get("href") if link else None
            if url and title:
                products.append(Product(title=title, price=price, currency=currency, url=url, store="ebay"))
        return products

    async def search_walmart(self, query: str) -> List[Product]:
        url = "https://www.walmart.com/search/?query=" + query.replace(" ", "%20")
        await self.page.goto(url, timeout=60000)
        await self.page.wait_for_timeout(1500)
        soup = BeautifulSoup(await self.page.content(), "html.parser")
        products = []
        for tile in soup.select("div.search-result-gridview-item-wrapper"):
            title_tag = tile.select_one("a.product-title-link span")
            price_tag = tile.select_one("span.price-main .visuallyhidden")
            link_tag = tile.select_one("a.product-title-link")
            title = title_tag.get_text(strip=True) if title_tag else None
            price_text = price_tag.get_text(strip=True) if price_tag else None
            url = ("https://www.walmart.com" + link_tag.get("href")) if link_tag else None
            price, currency = parse_price(price_text) if price_text else (None, None)
            if title and url:
                products.append(Product(title=title, price=price, currency=currency, url=url, store="walmart"))
        return products

    async def search_generic(self, site_url: str, query: str) -> List[Product]:
        try_urls = [
            f"{site_url.rstrip('/')}/search?q={query.replace(' ', '+')}",
            f"{site_url.rstrip('/')}/search/{query.replace(' ', '%20')}",
            f"{site_url.rstrip('/')}/?s={query.replace(' ', '+')}",
        ]
        results = []
        for u in try_urls:
            try:
                await self.page.goto(u, timeout=30000)
                await self.page.wait_for_timeout(1500)
                soup = BeautifulSoup(await self.page.content(), "html.parser")
                for a in soup.select("a"):
                    href = a.get("href")
                    text = a.get_text(strip=True)
                    if not href or not text:
                        continue
                    parent = a.parent
                    combined = " ".join([c.get_text(strip=True) for c in parent.select("*")]) if parent else text
                    price, currency = parse_price(combined)
                    if price or ("add to cart" in combined.lower()):
                        url = href if href.startswith("http") else site_url.rstrip("/") + href
                        results.append(Product(title=text, price=price, currency=currency, url=url, store="generic"))
                if results:
                    return results
            except Exception:
                continue
        return results


# ---------- Product selection ----------
class ProductSelector:
    def __init__(self, prefer_low_price: bool = True):
        self.prefer_low_price = prefer_low_price

    def rank(self, products: List[Product], constraints: Dict[str, Any]) -> List[Product]:
        filtered = []
        max_price = constraints.get("max_price")
        must_have = constraints.get("must_have", [])
        for p in products:
            if max_price is not None and p.price is not None and p.price > max_price:
                continue
            title = p.title.lower()
            if must_have:
                if not all(k.lower() in title for k in must_have):
                    continue
            filtered.append(p)
        if not filtered:
            filtered = products[:]
        def score(product: Product):
            s = 0
            if product.price:
                s += product.price
            return s
        filtered.sort(key=score, reverse=not self.prefer_low_price)
        return filtered


# ---------- Actions (add to cart, goto cart, checkout) ----------
class ActionExecutor:
    def __init__(self, page: Page):
        self.page = page

    async def open_product_page(self, product: Product):
        await self.page.goto(product.url, timeout=60000)
        await self.page.wait_for_timeout(1000)

    async def attempt_add_to_cart(self) -> bool:
        add_selectors = [
            "button#add-to-cart-button",
            "input#add-to-cart-button",
            "button[name='add']",
            "button.add-to-cart",
            "button:has-text('Add to cart')",
            "button:has-text('Add to Cart')",
            "button:has-text('Add to Basket')",
        ]
        for sel in add_selectors:
            try:
                el = await self.page.query_selector(sel)
                if el:
                    await el.scroll_into_view_if_needed()
                    await self.page.wait_for_timeout(400)
                    await el.click(timeout=15000)
                    await self.page.wait_for_timeout(1500)
                    return True
            except Exception:
                continue
        return False

    async def go_to_cart(self) -> bool:
        cart_selectors = [
            "a#nav-cart",
            "a[href*='/cart']",
            "a[aria-label*='cart']",
            "a:has-text('Cart')",
            "a:has-text('Basket')",
        ]
        for sel in cart_selectors:
            try:
                el = await self.page.query_selector(sel)
                if el:
                    await el.click()
                    await self.page.wait_for_timeout(1200)
                    return True
            except Exception:
                continue
        # fallback numeric path try /cart
        try:
            base = "/".join(self.page.url.split("/")[:3])
            await self.page.goto(base + "/cart", timeout=10000)
            await self.page.wait_for_timeout(1200)
            return True
        except Exception:
            pass
        return False

    async def proceed_to_checkout(self) -> bool:
        checkout_selectors = [
            "a#hlb-ptc-btn-native",
            "a[href*='/checkout']",
            "button:has-text('Proceed to checkout')",
            "button:has-text('Checkout')",
        ]
        for sel in checkout_selectors:
            try:
                el = await self.page.query_selector(sel)
                if el:
                    await el.click()
                    await self.page.wait_for_timeout(1200)
                    return True
            except Exception:
                continue
        try:
            base = "/".join(self.page.url.split("/")[:3])
            await self.page.goto(base + "/checkout", timeout=10000)
            await self.page.wait_for_timeout(1200)
            return True
        except Exception:
            pass
        return False

    async def fill_shipping(self, shipping: Dict[str, str]) -> bool:
        """
        Try to fill common shipping fields if present.
        shipping keys: first_name,last_name,address1,address2,city,state,zip,phone,email
        """
        mapping = {
            "first_name": ["input[name='firstName']", "input#firstName", "input[name='firstname']"],
            "last_name": ["input[name='lastName']", "input#lastName", "input[name='lastname']"],
            "address1": ["input[name='address1']", "input#addressLine1", "input[name='address1']"],
            "address2": ["input[name='address2']", "input#addressLine2"],
            "city": ["input[name='city']"],
            "state": ["input[name='state']", "select[name='state']"],
            "zip": ["input[name='postalCode']", "input[name='zip']"],
            "phone": ["input[name='phone']"],
            "email": ["input[name='email']"],
        }
        success = False
        for key, candidates in mapping.items():
            val = shipping.get(key)
            if not val:
                continue
            for sel in candidates:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        await el.fill(val)
                        success = True
                        break
                except Exception:
                    continue
        return success


# ---------- LLM Planner using google-genai ----------
class LLMPlanner:
    def __init__(self, client: genai.Client = genai_client, model: str = "models/gemini-2.0-flash"):
        self.client = client
        self.model = model

    def plan(self, user_request: str) -> Dict[str, Any]:
        prompt = f"""
Convert the following user shopping request into JSON with fields:
- query: short search phrase
- store: one of ['amazon','ebay','walmart','generic'] or null
- max_price: numeric max price or null
- must_have: list of keywords that must be present

Only output valid JSON.

Request: \"\"\"{user_request}\"\"\"
"""
        resp = self.client.models.generate_content(model=self.model, contents=prompt)
        text = resp.text.strip()
        j = re.search(r"\{.*\}", text, re.DOTALL)
        if j:
            text = j.group(0)
        try:
            plan = json.loads(text)
            return plan
        except Exception:
            # fallback heuristics
            m = re.search(r'under\s*\$?([0-9]+)', user_request)
            max_price = float(m.group(1)) if m else None
            store = None
            for s in ["amazon", "ebay", "walmart"]:
                if s in user_request.lower():
                    store = s
            return {"query": user_request, "store": store, "max_price": max_price, "must_have": []}

# app.py
import os
import asyncio
import base64
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from agent import (
    BrowserController, StoreScraper, ProductSelector, ActionExecutor, LLMPlanner, Product
)


app = FastAPI(title="Agentic Shopping API")

# Plan + Search request model
class PlanRequest(BaseModel):
    user_request: str
    site_hint: Optional[str] = None  # 'amazon'|'ebay'|'walmart'|'generic'
    headless: Optional[bool] = True

class ChooseRequest(BaseModel):
    product_index: Optional[int] = None
    product_url: Optional[str] = None
    headless: Optional[bool] = True

class CheckoutRequest(BaseModel):
    shipping: Optional[Dict[str, str]] = None
    headless: Optional[bool] = True

# In-memory session store (for demo). In production use a DB or Redis.
SESSIONS: Dict[str, Dict[str, Any]] = {}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/plan_and_search")
async def plan_and_search(req: PlanRequest):
    planner = LLMPlanner()
    plan = planner.plan(req.user_request)
    query = plan.get("query") or req.user_request
    store = plan.get("store") or req.site_hint
    max_price = plan.get("max_price")
    must_have = plan.get("must_have", [])
    constraints = {"max_price": max_price, "must_have": must_have}

    async with BrowserController(headless=req.headless) as bc:
        page = await bc.new_page()
        scraper = StoreScraper(page)
        products = []
        # Prefer specified store, otherwise try top stores
        if store == "amazon":
            products = await scraper.search_amazon(query)
        elif store == "ebay":
            products = await scraper.search_ebay(query)
        elif store == "walmart":
            products = await scraper.search_walmart(query)
        else:
            products = await scraper.search_amazon(query)
            if len(products) < 4:
                products += await scraper.search_ebay(query)
            if len(products) < 6:
                products += await scraper.search_walmart(query)
            if len(products) < 6:
                products += await scraper.search_generic("https://www.example.com", query)

        selector = ProductSelector()
        ranked = selector.rank(products, constraints)
        # create session id for this browsing session
        sid = base64.urlsafe_b64encode(os.urandom(9)).decode()
        SESSIONS[sid] = {"plan": plan, "products": ranked, "page_url": None, "last_page_html": None}
        # Return top N products (limited info)
        out = []
        for i, p in enumerate(ranked[:10]):
            out.append({"index": i, "title": p.title, "price": p.price, "currency": p.currency, "url": p.url, "store": p.store})
        return {"session_id": sid, "plan": plan, "products": out}

@app.post("/choose")
async def choose(session_id: str, body: ChooseRequest):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    session = SESSIONS[session_id]
    products = session["products"]
    chosen = None
    if body.product_url:
        for p in products:
            if p.url == body.product_url:
                chosen = p
                break
    elif body.product_index is not None:
        if 0 <= body.product_index < len(products):
            chosen = products[body.product_index]
    if not chosen:
        raise HTTPException(status_code=400, detail="Product not found in session")

    async with BrowserController(headless=body.headless) as bc:
        page = await bc.new_page()
        executor = ActionExecutor(page)
        await executor.open_product_page(chosen)
        added = await executor.attempt_add_to_cart()
        page_url = page.url
        # capture screenshot to return to caller for verification
        screenshot = await page.screenshot(full_page=False)
        screenshot_b64 = base64.b64encode(screenshot).decode()
        session["page_url"] = page_url
        session["chosen"] = chosen
        session["last_page_html"] = await page.content()
        # Note: We do not keep the browser open across requests in this simple demo
    return {"status": "added" if added else "needs_manual_add", "page_url": page_url, "screenshot_b64": screenshot_b64}

@app.post("/checkout")
async def checkout(session_id: str, body: CheckoutRequest):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    session = SESSIONS[session_id]
    chosen: Product = session.get("chosen")
    if not chosen:
        raise HTTPException(status_code=400, detail="No product chosen for this session")

    async with BrowserController(headless=body.headless) as bc:
        page = await bc.new_page()
        executor = ActionExecutor(page)
        # go to cart
        await page.goto(chosen.url, timeout=60000)
        # Attempt to add again if needed
        await executor.attempt_add_to_cart()
        await executor.go_to_cart()
        # Try proceed to checkout
        proceeded = await executor.proceed_to_checkout()
        # Optionally fill shipping details if provided (but do not enter card details)
        filled = False
        if body.shipping:
            filled = await executor.fill_shipping(body.shipping)
            # Wait a bit to let site validate
            await page.wait_for_timeout(1000)
        checkout_url = page.url
        screenshot = await page.screenshot(full_page=False)
        screenshot_b64 = base64.b64encode(screenshot).decode()
        # IMPORTANT: do not submit payment. Return checkout url to the user.
    return {
        "status": "at_checkout" if proceeded else "could_not_navigate_to_checkout",
        "checkout_url": checkout_url,
        "filled_shipping": filled,
        "screenshot_b64": screenshot_b64,
        "note": "Agent stopped before payment. Please verify and complete payment manually in the browser."
    }

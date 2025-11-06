---

# 🛒 Agentic AI Shopping Assistant

> **An autonomous AI agent that browses, compares, and purchases products on e-commerce websites using Playwright automation and Google Gemini intelligence.**

---

## 🌍 Overview

The **Agentic AI Shopping Assistant** is a next-generation autonomous system designed to simulate human-like shopping behavior online. It can:

✅ **Understand** user shopping intents via FastAPI endpoints.
🧠 **Reason, plan, and decide** on the best shopping strategy using **Google Gemini**.
🌐 **Control** a real Chromium-based browser with **Playwright** for seamless web interaction.
🛍️ **Perform** autonomous product searches, comparisons, and checkouts on major e-commerce sites (Amazon, eBay, or custom stores).

> Built **completely from scratch** — no external agent frameworks.
> Only **core Python, Playwright, and Gemini APIs** power this intelligent system.

---

## 🧠 Tech Stack

| 🧩 **Component**         | ⚙️ **Technology**                                        |
| ------------------------ | -------------------------------------------------------- |
| **LLM**                  | [Google Gemini](https://ai.google.dev/) (`google-genai`) |
| **Web Automation**       | [Playwright (Chromium)](https://playwright.dev/python/)  |
| **Backend API**          | [FastAPI](https://fastapi.tiangolo.com/)                 |
| **Async Runtime**        | `asyncio`                                                |
| **Programming Language** | Python 3.10+                                             |

---

## 🚀 Key Features

✨ **Autonomous Shopping** — searches, compares, and simulates purchasing products automatically.
🧭 **Goal-Oriented Planning** — Gemini LLM generates structured multi-step action plans.
💬 **Natural Language Input** — users can describe what they want to buy in plain English.
🧠 **Reasoning Loop** — combines perception (Playwright scraping) with LLM reasoning.
⚡ **Async & Scalable** — built with FastAPI and asyncio for speed and concurrency.

---

Absolutely! Here’s that entire section beautifully formatted and structured in **modern, professional Markdown style**, perfect for your `README.md`.
It uses icons, spacing, code highlighting, and note formatting for clarity 👇

---

## 🧩 4️⃣ Run the Server

Start your FastAPI application with environment variables configured:

```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

> ⚙️ **Note:** Use `--reload` only in development mode — it auto-restarts the server when code changes.

---

## 🧪 5️⃣ Example Usage

Below are example API calls using `curl` to interact with the agentic AI shopping API.

---

### 🧠 **Plan & Search**

Initiates a product search and reasoning plan.

```bash
curl -X POST "http://127.0.0.1:8000/plan_and_search" \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Buy a black wool sweater under $60 on eBay",
    "site_hint": "ebay",
    "headless": false
  }'
```

🧾 **Response Example:**

```json
{
  "session_id": "ebay_1736162346",
  "products": [
    {
      "title": "Men's Black Wool Sweater - Medium",
      "price": "$54.99",
      "link": "https://www.ebay.com/itm/1234567890"
    },
    ...
  ]
}
```

> 💡 Returns a `session_id` and a list of recommended products.

---

### 🛒 **Choose (Add to Cart)**

Selects a specific product (by index) from the previous search and adds it to the cart.

```bash
curl -X POST "http://127.0.0.1:8000/choose?session_id=THE_SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "product_index": 0,
    "headless": false
  }'
```

🧾 **Response Example:**

```json
{
  "status": "success",
  "page_url": "https://www.ebay.com/cart",
  "screenshot_base64": "<base64-image-data>"
}
```

> 🖼️ Returns the active cart page URL and a screenshot preview (Base64 encoded).

---

### 💳 **Checkout (Manual Completion)**

Navigates to checkout and optionally fills out shipping details.
You’ll still complete payment manually for security and compliance.

```bash
curl -X POST "http://127.0.0.1:8000/checkout?session_id=THE_SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "shipping": {
      "first_name": "Alice",
      "last_name": "Smith",
      "address1": "123 Example St",
      "city": "Anytown",
      "state": "CA",
      "zip": "94000",
      "phone": "555-555-5555",
      "email": "alice@example.com"
    },
    "headless": false
  }'
```

🧾 **Response Example:**

```json
{
  "checkout_url": "https://www.ebay.com/checkout",
  "screenshot_base64": "<base64-image-data>"
}
```

> ⚠️ **Security Reminder:**
> The agent never handles card data. You must open the returned `checkout_url` manually to finish payment.

---

## 🛡️ 6️⃣ Notes, Improvements & Production Readiness

### 🧠 **Session Persistence**

* Currently uses **in-memory** session tracking.
* Replace with **Redis** or a database (e.g., PostgreSQL, MongoDB) for production stability.

### 🔐 **Authentication**

* Add **user authentication** (JWT / OAuth2) and access control for sensitive endpoints.

### 🧩 **Secure Secrets**

* Never hardcode API keys or credentials in source code.
* Use environment variables or a secret manager (e.g., **AWS Secrets Manager**, **Vault**, **Google Secret Manager**).

### 💸 **Payment Automation (Highly Restricted)**

If you experiment with automating payment steps:

* Store credentials securely using a vault solution.
* Require **explicit user consent** and **2FA / signed requests** before submission.
* Maintain an **audit log** of all transactions.
* Always comply with **merchant Terms of Service** and **legal regulations**.

> ⚠️ *This repository intentionally omits payment automation logic for ethical and compliance reasons.*

---

### 🧭 **Headless vs. Headed Mode**

* Many e-commerce sites detect and block pure headless browsers.
* Use `headless=False` for visible simulation and human-like interactions.

### 🕵️‍♂️ **Stealth & Realism**

* Randomize interaction patterns — such as viewport size, mouse movements, and typing delays — to simulate real users.
* However, always **respect site terms and conditions**.

### 🧱 **Site-Specific Selectors**

* Each site uses different DOM structures.
* Implement **per-site selector modules** for robust “add to cart” and “checkout” flows.
* Example: `selectors/amazon.py`, `selectors/ebay.py`, etc.

---

Got it 👍 — here’s your **updated, clean, and beautiful markdown** version of the installation section using **`uv`** instead of `pip` and **without** a `requirements.txt` file.

---

# ⚙️ Installation Guide

### 🧭 1️⃣ Clone the Repository

```bash
git clone https://github.com/charithmadhuranga/agentic-ai-shopper.git
cd agentic-ai-shopper
```

---

### 🧩 2️⃣ Create and Activate a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

Or if you use **uv** (recommended for speed 🚀):

```bash
uv venv
source .venv/bin/activate
```

---

### 📦 3️⃣ Install Dependencies

Since this project doesn’t use `requirements.txt`, install all packages directly:

```bash
uv pip install fastapi uvicorn playwright google-genai python-dotenv
```

---

### 🌐 4️⃣ Install Playwright Browsers

```bash
playwright install
```

This installs the required Chromium browser engines for the agent to operate.

---

### 🔑 5️⃣ Setup Environment Variables

Create a `.env` file in your project root and add your Google Gemini API key:

```bash
GEMINI_API_KEY=your_google_gemini_api_key_here
```

Or export it directly in your shell (temporary):

```bash
export GEMINI_API_KEY="your_google_gemini_api_key_here"
```

---

### 🚀 6️⃣ Run the Server

Use **Uvicorn** to start the FastAPI backend:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

> 💡 The `--reload` flag automatically restarts the server when files change.
> Use it **only for development**.

---

### ✅ 7️⃣ Verify Setup

Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
You should see the FastAPI Swagger UI where you can test endpoints interactively.

---




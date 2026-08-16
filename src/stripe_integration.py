#!/usr/bin/env python3
"""
Stripe Integration — Platební brána pro Asgard Lab.

Přidává do Asgard Lab:
  POST /subscribe       — vytvořit předplatné (checkout session)
  POST /webhook         — Stripe webhook (potvrzení platby)
  GET  /pricing         — ceník

Ceník (Standard 700):
  GEALL_111   = 111 CZK/měsíc
  KAREL_222   = 222 CZK/měsíc
  DUBBING_333 = 333 CZK/měsíc
  FAMILY_423  = 423 CZK/měsíc
  SIGN_FREE   = 0 CZK (znakový jazyk ZDARMA)

Autor: Pan Jeskyně
"""

import os
import stripe
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

# === STRIPE CONFIG ===
STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY", "")
if not STRIPE_SECRET:
    key_file = Path.home() / ".stripe_secret_key"
    if key_file.exists():
        STRIPE_SECRET = key_file.read_text().strip()

STRIPE_PUBLISHABLE = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
if not STRIPE_PUBLISHABLE:
    key_file = Path.home() / ".stripe_publishable_key"
    if key_file.exists():
        STRIPE_PUBLISHABLE = key_file.read_text().strip()

STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

stripe.api_key = STRIPE_SECRET

# === CENÍK ===
PLANS = {
    "geall_111": {
        "name": "Geall AI Assistant",
        "price_czk": 111,
        "features": ["AI asistent", "Textový překlad", "1 zařízení"],
    },
    "karel_222": {
        "name": "Karel IV — Real-time Voice",
        "price_czk": 222,
        "features": ["Real-time překlad", "Voice clone", "Kvalitní mód", "2 zařízení"],
    },
    "dubbing_333": {
        "name": "Stream Dubbing",
        "price_czk": 333,
        "features": ["Stream dubbing", "Separace mluvčích", "Smart TV", "5 zařízení"],
    },
    "family_423": {
        "name": "Family 4:23",
        "price_czk": 423,
        "features": ["Vše bez omezení", "Celá rodina", "Mesh priorita", "∞ zařízení"],
    },
    "sign_free": {
        "name": "Znakový jazyk",
        "price_czk": 0,
        "features": ["Znakový jazyk", "ZDARMA navždy", "Pro neslyšící komunitu"],
    },
}

# === ROUTER ===
router = APIRouter()


@router.get("/pricing")
async def pricing():
    """Ceník předplatného."""
    return {
        "currency": "CZK",
        "plans": PLANS,
        "principle": "1+1=3",
        "sign_language": "ALWAYS FREE for deaf community",
    }


@router.post("/subscribe")
async def subscribe(plan_id: str, success_url: str = "https://app.web4light.online/",
                    cancel_url: str = "https://app.web4light.online/"):
    """Vytvořit Stripe Checkout Session pro předplatné."""
    
    if plan_id not in PLANS:
        raise HTTPException(400, f"Unknown plan: {plan_id}")
    
    plan = PLANS[plan_id]
    
    if plan["price_czk"] == 0:
        # Znakový jazyk je zdarma — žádná platba
        return {"status": "free", "plan": plan_id, "message": "Znakový jazyk je ZDARMA. Žádná platba potřeba."}
    
    if not STRIPE_SECRET or STRIPE_SECRET.startswith("#"):
        raise HTTPException(503, "Payment system not yet activated. Identity verification pending.")
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price_data": {
                    "currency": "czk",
                    "product_data": {
                        "name": plan["name"],
                        "description": " + ".join(plan["features"]),
                    },
                    "unit_amount": plan["price_czk"] * 100,  # Stripe expects halíře
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }],
            success_url=success_url + "?payment=success",
            cancel_url=cancel_url + "?payment=cancelled",
        )
        
        return {"checkout_url": session.url, "session_id": session.id}
    
    except stripe.error.StripeError as e:
        raise HTTPException(500, f"Stripe error: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Stripe webhook — potvrzení platby."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    
    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        else:
            event = stripe.Event.construct_from(
                stripe.util.json.loads(payload), stripe.api_key
            )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(400, "Invalid webhook")
    
    # Zpracovat události
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        print(f"[STRIPE] ✅ New subscription! Customer: {session.get('customer_email', 'unknown')}")
    
    elif event["type"] == "invoice.paid":
        invoice = event["data"]["object"]
        amount = invoice.get("amount_paid", 0) / 100
        print(f"[STRIPE] 💰 Payment received: {amount} CZK")
    
    elif event["type"] == "customer.subscription.deleted":
        print(f"[STRIPE] ❌ Subscription cancelled")
    
    return {"status": "ok"}

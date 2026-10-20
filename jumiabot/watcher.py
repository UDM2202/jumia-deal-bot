"""Checks your watch list and the flash-sale page, and alerts on Telegram."""
import html
import logging

from .scraper import JumiaClient

log = logging.getLogger(__name__)


def matches(product, rule):
    name = product.name.lower()
    if any(word.lower() not in name for word in rule.get("include", [])):
        return False
    if any(word.lower() in name for word in rule.get("exclude", [])):
        return False
    if product.price is None:
        return False
    if rule.get("min_price") and product.price < rule["min_price"]:
        return False
    if rule.get("max_price") and product.price > rule["max_price"]:
        return False
    if rule.get("min_discount") and product.effective_discount < rule["min_discount"]:
        return False
    return True


def format_alert(product, label):
    lines = [f"🔥 <b>{html.escape(label)}</b>", html.escape(product.name)]
    price = f"₦{product.price:,.0f}"
    if product.old_price:
        price += f" <s>₦{product.old_price:,.0f}</s>"
    if product.effective_discount:
        price += f"  (-{product.effective_discount}%)"
    lines.append(price)
    if product.items_left is not None:
        lines.append(f"⚠️ Only {product.items_left} left")
    lines.append(product.url)
    return "\n".join(lines)


def should_alert(state, product):
    """Alert on first sighting, or when the price drops again."""
    last = state.data["deals"].get(product.key)
    return last is None or product.price < last


def check_deals(cfg, state, telegram):
    client = JumiaClient(cfg["base_url"], cfg.get("request_delay_seconds", 2.0))
    sent = 0

    for rule in cfg.get("watches", []):
        try:
            products = client.search(rule["query"], pages=rule.get("pages", 1), sort=rule.get("sort"))
        except Exception as e:  # network errors, Jumia blocking, etc.
            log.warning("Search %r failed: %s", rule["query"], e)
            continue
        log.info("%s: %d products scanned", rule["name"], len(products))
        for p in products:
            if matches(p, rule) and should_alert(state, p):
                telegram.send(format_alert(p, rule["name"]))
                state.data["deals"][p.key] = p.price
                sent += 1

    fs = cfg.get("flash_sales") or {}
    if fs.get("enabled"):
        try:
            products = client.listing(fs.get("path", "/flash-sales/"), pages=fs.get("pages", 2), flash_sale=True)
        except Exception as e:
            log.warning("Flash sales page failed: %s", e)
            products = []
        log.info("Flash sales: %d products scanned", len(products))
        rule = {"min_discount": fs.get("min_discount", 0), "max_price": fs.get("max_price")}
        keywords = [k.lower() for k in fs.get("keywords", [])]
        for p in products:
            if keywords and not any(k in p.name.lower() for k in keywords):
                continue
            if matches(p, rule) and should_alert(state, p):
                telegram.send(format_alert(p, "Flash sale"))
                state.data["deals"][p.key] = p.price
                sent += 1

    return sent

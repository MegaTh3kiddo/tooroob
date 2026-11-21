# Demo Video Narration Script (About 5 Minutes)

> Pacing: Part 1 about 3.5 minutes, Part 2 about 1.5 minutes. Each paragraph = one slide.

**1 · Title (15 seconds)** — "We built TorobMap: an in-person shopping assistant in Tehran. From 'Where is it cheaper?' to 'I'm sure it's in stock right now.' A mobile web app, the TorobChat assistant, and the seller Android app."

**2 · Problem (20 seconds)** — "In in-person shopping we have four pain points: prices vary, stock is unclear, the shop might be closed, and manual follow-up is hard."

**3 · Four Steps (15 seconds)** — "The challenge had four steps: search, comparison, nearby seller, follow-up. We covered all four, and not everything has to go through chat."

**4 · TorobChat (30 seconds)** — "TorobChat understands the need, asks only the necessary question—like budget—with buttons. Then it gives recommendations and has a reason for each card: price relative to the market, store trust, and probability of stock."

**5 · List & Comparison (20 seconds)** — "You can do it without chat too: search, filter, compare two stores, cheapest or nearest."

**6 · Map (20 seconds)** — "On the map you see nearby sellers, with distance and travel time, and a multi-shop visit plan that warns you before the shop closes."

**7 · Transparency (25 seconds)** — "We don't treat recorded price, time of price change, and verified stock as the same thing. Whatever is unclear we explicitly call unclear; and no seller response is ever fabricated."

**8 · Inquiry System (30 seconds)** — "The heart of the product: 'Have Torob inquire for me.' First a gate calculates whether asking is worth it. Then a push goes to the seller app, with reminders and urgent call, and a real response comes back."

**9 · One Inquiry, Two Phones (20 seconds)** — "These are the four steps: the customer taps, the seller's phone rings, the seller enters the exact price and quantity, and the customer sees the response with a tracking code."

**10 · Seller App (20 seconds)** — "The seller sees a full-screen call screen with a response countdown and answers with one tap. Declining requires a reason, so even saying no has evidence. Offline responses are queued too."

**11 · Live Demo (40 seconds, play the video)** — "Right now on two phones: customer on the right, seller on the left. Chat, list, map, inquiry… the seller's phone rings… the seller answers… and the response lands live on the customer's phone."

**12 · Jimbo & Deployment (15 seconds)** — "The Jimbo test store with 17 real items is connected to the seller app. The web app and API are two independent apps on Liara."

— Part 2: System Design —

**13 · Architecture (25 seconds)** — "The web app reaches FastAPI; the catalog is in DuckDB and the evidence ledger is in SQLite. Every seller response is an evidence event that updates store trust and stock probability."

**14 · Inventory Algorithm (25 seconds)** — "Being in stock isn't yes/no; it's a probability that decays over time: S equals exp of negative lambda times quantity and time. With a quantity of one it decays faster than with more than five. If the seller says out of stock it becomes zero."

**15 · Inquiry Method (25 seconds)** — "We only bother the seller when it's worth it: quiet hours, daily cap, cooldown period, and the value-of-information formula. Responses are idempotent and zero stays zero."

**16 · Pricing & Trust (20 seconds)** — "Absurd prices are filtered out, we compare against the peer median, and store trust is multidimensional and Bayesian, so a new shop isn't unfairly penalized."

**17 · Summary (20 seconds)** — "225 thousand products, 331 thousand offers, 6.5 thousand stores, and 157 tests. Honest with data, generous with the user. Thanks."

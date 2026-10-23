# TorobChat — Connecting an LLM Provider

TorobChat works **fully offline** by default: a deterministic Persian parser handles intent and constraints, and
the evidence-based recommender ranks real catalogue offers. An external LLM is **optional**. You can add one through
any **OpenAI-compatible** `/chat/completions` API: OpenAI, BoxAPI, OpenRouter, Gemini's OpenAI endpoint, or a
self-hosted vLLM, Ollama or LiteLLM gateway.

## What the LLM is allowed to do (and what it is not)

| Step | Who does it | Notes |
| --- | --- | --- |
| Parse intent and constraints | Deterministic parser first. The LLM **only fills fields the parser missed**: product noun, brand, budget min/max | It never overrides what the parser understood. Budgets outside 10,000–100,000,000,000 Toman are ignored |
| Clarifying questions (budget → brand) | Deterministic `ClarificationPolicy` | Each question has structured `options` that the UI renders as tappable chips |
| Retrieval, price checks, stock survival, shop trust, ranking | Deterministic engines only | All prices, stock and trust figures come from the catalogue and the evidence ledger |
| Final reply wording | The LLM rephrases the grounded draft (`TOROB_LLM_POLISH_REPLIES`) | **Number guard:** if the LLM output contains *any* number that is not in the grounded draft, it is discarded and the grounded text is used |

Any provider error (timeout, 4xx/5xx, malformed JSON) is logged as a warning, and the chat continues in deterministic
mode. The user never sees an error.

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `TOROB_LLM_PROVIDER` | `openai_compatible` | Set `none` to force offline mode even if a key is present |
| `TOROB_LLM_API_KEY` | — | API key, sent as `Authorization: Bearer <key>`. Falls back to `OPENAI_API_KEY` / `GEMINI_API_KEY`. With no key, the LLM is disabled |
| `TOROB_LLM_BASE_URL` | `https://api.openai.com/v1` | Base URL. The code appends `/chat/completions` |
| `TOROB_LLM_MODEL` | `gpt-4o-mini` | Model name, passed through unchanged |
| `TOROB_LLM_TIMEOUT_SECONDS` | `12` | Per-request timeout |
| `TOROB_LLM_POLISH_REPLIES` | `true` | `false` keeps the LLM for parsing only and returns grounded text verbatim |

Keys whose value starts with `mock` or `dummy` are treated as "no key".

## Examples

**OpenAI**
```bash
TOROB_LLM_API_KEY=sk-...
TOROB_LLM_BASE_URL=https://api.openai.com/v1
TOROB_LLM_MODEL=gpt-4o-mini
```

**BoxAPI** (Iranian gateway to OpenAI, Claude, Gemini and more; OpenAI request format)
```bash
TOROB_LLM_API_KEY=<your BoxAPI key>
TOROB_LLM_BASE_URL=https://ai.boxapi.ir/ai/v1
TOROB_LLM_MODEL=gpt-5.4-mini        # any model id listed in your BoxAPI panel
```
BoxAPI's documented endpoint is `https://ai.boxapi.ir/ai/v1/chat/completions` with a Bearer token. Check the exact
model ids in your BoxAPI panel or at https://boxapi.ir/docs/.

**Any OpenAI-compatible gateway** (OpenRouter, LiteLLM, vLLM, Ollama, ...)
```bash
TOROB_LLM_BASE_URL=https://openrouter.ai/api/v1     # or http://<host>:11434/v1 for Ollama
TOROB_LLM_API_KEY=<key>                            # Ollama accepts any non-empty value
TOROB_LLM_MODEL=<model id>
```

**Gemini (OpenAI-compatible endpoint)**
```bash
TOROB_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
TOROB_LLM_API_KEY=<Gemini key>
TOROB_LLM_MODEL=gemini-2.0-flash
```

## Setting it on Liara

From the Liara panel: open the backend app → **Settings → Environment variables** → add the variables → save.
The app restarts automatically.

From the CLI:
```bash
liara env set --app <backend-app-name> \
  "TOROB_LLM_API_KEY=<key>" \
  "TOROB_LLM_BASE_URL=https://ai.boxapi.ir/ai/v1" \
  "TOROB_LLM_MODEL=gpt-5.4-mini"
```
To disable it again: `liara env set --app <backend-app-name> "TOROB_LLM_PROVIDER=none"`.

Never commit keys. `.env` is git-ignored, and `.env.example` lists the variable names only.

## Where the code lives

| File | Role |
| --- | --- |
| `src/torob/agent/llm.py` | `OpenAICompatibleProvider` (HTTP client), `get_llm_client()` (env config), `llm_extract_constraints()`, `llm_polish_reply()` (with the number guard), `DeterministicFallbackParser` |
| `src/torob/agent/orchestrator.py` | `process_message()`: deterministic parse → `_apply_llm_constraints()` → topic-change reset → clarification → recommendation → optional polish |
| `src/torob/agent/clarification.py` | Clarification policy (budget, then brand for phones/laptops in the guided flow, location, workload) |
| `src/torob/agent/recommender.py` | Evidence-based retrieval and ranking, including model-vs-model comparison (`_retrieve_text_comparison`) |
| `src/torob/api/v1/endpoints_assistant.py` | REST API: `POST /api/v1/assistant/sessions`, `POST /api/v1/assistant/sessions/{id}/messages` |
| `trobapp/public/js/backend.js` | Web chat bridge: renders clarification chips, recommendation cards, the comparison table and the inquiry buttons |

## Conversation flow (works with or without an LLM)

1. «گوشی میخوام» → asks for budget (chips: «زیر ۱۵ میلیون تومان», …)
2. Tap a budget → asks for brand (chips: «سامسونگ», «شیائومی», «اپل (آیفون)», «برایم فرقی نمی‌کند»)
3. Tap a brand → ranked list. Each card shows price vs. market median, shop trust, stock probability, a trade-off
   label (best overall / budget pick / most reliable shop) and an inquiry button.
4. «مقایسه آیفون ۱۳ و سامسونگ S23» → side-by-side table (lowest real price, market median, shop trust, stock
   probability) plus offer cards.
5. Starting a new product type («حالا لپ تاپ میخوام») resets the previous budget and brand and restarts the guided
   questions.

Detailed one-shot requests («هدفون بی سیم زیر ۳ میلیون», «لپ تاپ تا سقف ۶۰ میلیون») skip the questions and return results
right away.

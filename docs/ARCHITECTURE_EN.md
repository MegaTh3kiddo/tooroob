# 🏛️ System Architecture & Decision Engine (TorobMap)

<p align="center">
  <b>🌐 Language / زبان:</b>
  <a href="ARCHITECTURE.md"><b> 🇮🇷 فارسی</b></a> |
  <a href="ARCHITECTURE_EN.md"><b> 🇬🇧 English (Current)</b></a>
</p>

---

> This document describes the system architecture, end-to-end data flow, probabilistic inference engines, and SLA escalation ladder of the **TorobMap** platform.

---

## 1. System Overview & Inquiry Lifecycle

TorobMap addresses the high cost of failed in-person shopping trips (Tehran traffic congestion, wasted travel time, out-of-stock items, or outdated prices). Instead of relying on static scraped prices, the system uses an **evidence-driven probabilistic framework**:

```mermaid
flowchart TB
    subgraph Clients["User & Client Apps"]
        WebShopper[" In-Person Shopper<br/>(trobapp · Next.js 14)"]
        MerchantAndroid[" Store Merchant<br/>(torob_merchant_app · Jetpack Compose)"]
        LandlinePhone[" Store Landline Phone<br/>(Poshteyar Persian Voice TTS)"]
    end

    subgraph Gateway["Gateway & Proxy"]
        NextProxy["Next.js API Route Proxy<br/>/api/v1/*"]
        FastAPIGw["FastAPI Gateway & Auth<br/>CORS / Rate Limiting"]
    end

    subgraph Intelligence["Intelligence & Statistical Engines"]
        VoIEngine["Value of Information (VoI)<br/>Information Gain vs Interruption Cost"]
        PriceEngine["Price Intelligence Engine<br/>Leave-One-Out Peer Median & Unit Checks"]
        StockHazard["Stock Survival Hazard Model<br/>ETA Hazard Model with Travel Time"]
        BayesTrust["Bayesian Shop Trust Model<br/>Beta-Binomial with Time Decay"]
        TorobChatRAG["TorobChat AI Assistant<br/>RAG over 225k Items & 6.4k Physical Stores"]
    end

    subgraph Storage["Database & Storage Layer"]
        DuckDBCatalog[("Catalog Analytics Store<br/>DuckDB Vector/Columnar")]
        EvidenceLedger[("Evidence Ledger DB<br/>SQLite WAL Mode")]
    end

    subgraph Escalation["SLA Escalation Ladder"]
        L1["Stage 1: Instant Push Notification (0 - 30s)"]
        L2["Stage 2: Urgent Call Overlay URGENT_CALL (30 - 120s)"]
        L3["Stage 3: Automated Voice Call to Landline (120 - 180s)"]
        L4["Stage 4: Expiration & Re-routing to Alternative Stores"]
    end

    WebShopper -->|1. Search / Chat with TorobChat| NextProxy
    NextProxy --> FastAPIGw
    FastAPIGw --> Intelligence
    Intelligence <--> Storage

    FastAPIGw -->|Evaluate Dispatch Need| VoIEngine
    VoIEngine -->|Positive VoI| Escalation

    L1 --> MerchantAndroid
    L2 --> MerchantAndroid
    L3 --> LandlinePhone

    MerchantAndroid -->|Real-Time Merchant Response| FastAPIGw
    FastAPIGw -->|Commit Concrete Evidence| EvidenceLedger
    EvidenceLedger -->|Update Trust & Survival Models| Intelligence
    FastAPIGw -->|Stream Result to Shopper| WebShopper
```

---

## 2. Statistical Inference Engines & Mathematical Formulations

### A) Price Reasonableness & Unit Discrepancy Detection
To evaluate a store's listed price without introducing self-bias, the system computes the **Leave-One-Out Peer Median**:

```math
\tilde{P}_{-i} = \operatorname{Median}\left(\{P_j : j \in \mathcal{S}_{\mathrm{peer}}, j \neq i\}\right)
```

- If $|P_i - \tilde{P}\_{-i}| \approx 9 \times P_i$ or $P_i / \tilde{P}\_{-i} \in [9.5, 10.5]$ or $[0.095, 0.105]$, an automated Rial-versus-Toman 10x denomination error is flagged.

### B) Stock Arrival Hazard Model
In-person shopping involves transit time. The probability that an item remains in stock upon customer arrival is modeled as an exponential survival function:

```math
S(t_{\mathrm{ETA}}) = \exp(-\lambda \cdot t_{\mathrm{ETA}})
```

Where:
- $t\_{\mathrm{ETA}}$ is the estimated travel time in minutes based on real-time city transit patterns.
- $\lambda$ is the store departure rate, factoring in item popularity and historical store sales velocity:

```math
\lambda = \lambda_0 \cdot \gamma_{\mathrm{popularity}} \cdot \gamma_{\mathrm{store\_velocity}}
```

### C) Bayesian Shop Trust Model
A merchant's reliability $\theta$ is modeled with a conjugate Beta-Binomial distribution with prior $\operatorname{Beta}(\alpha\_0, \beta\_0)$ and Bayesian shrinkage:

```math
\alpha_{\mathrm{new}} = \alpha_{\mathrm{old}} \cdot e^{-\Delta t / \tau} + k
```

```math
\beta_{\mathrm{new}} = \beta_{\mathrm{old}} \cdot e^{-\Delta t / \tau} + (n - k)
```

```math
\hat{\theta} = \frac{\alpha_{\mathrm{new}}}{\alpha_{\mathrm{new}} + \beta_{\mathrm{new}}}
```

The parameter $e^{-\Delta t / \tau}$ applies a time decay, giving higher weight to recent merchant interactions.

### D) Value of Information (VoI) Inquiry Policy
Dispatching notifications or voice calls incurs a nuisance cost. An inquiry is only dispatched if the expected uncertainty reduction outweighs the interruption cost:

```math
\mathrm{VoI} = \Delta \mathrm{Certainty} \times \mathrm{TransactionValue} - \mathrm{InterruptionCost} > 0
```

---

## 3. SLA Escalation Ladder

1. **0 – 30s (Silent Push)**: Standard background push notification to merchant app.
2. **30 – 120s (Urgent Call Takeover)**: Android foreground service activates an incoming-call screen overlay with continuous ringtone (`androidapp-4.png`).
3. **120 – 180s (Voice Fallback)**: Automated Persian speech synthesis bot (Poshteyar TTS) places a voice call to the physical store's landline phone.
4. **Post 180s (Expiration)**: Inquiry expires gracefully; the shopper is notified and offered alternative nearby stores.

---

## 4. Related Documentation

- 🌐 [Shopper Web App Guide (WEB_APP_EN.md)](WEB_APP_EN.md)
- 📱 [Merchant Android Platform (MERCHANT_APP_EN.md)](MERCHANT_APP_EN.md)
- 🧠 [Intelligence Backend (INTELLIGENCE_ENGINE_EN.md)](INTELLIGENCE_ENGINE_EN.md)
- 📸 [Screenshots Catalog (screenshots/README_EN.md)](../screenshots/README_EN.md)

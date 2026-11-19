# 🧠 Intelligence Engine, Statistical Models & Central Backend

<p align="center">
  <b>🌐 Language / زبان:</b>
  <a href="INTELLIGENCE_ENGINE.md"><b> 🇮🇷 فارسی</b></a> |
  <a href="INTELLIGENCE_ENGINE_EN.md"><b> 🇬🇧 English (Current)</b></a>
</p>

---

> This document details the technical specifications, probabilistic decision models, data pipelines, and REST APIs implemented in the [`torob/`](../torob/) backend module.

---

## 1. Role & Architectural Responsibilities

The intelligence backend acts as the computational engine of TorobMap. Rather than simply serving static database records, it runs four active inference models in real time:

1. **Price Reasonableness & Currency Denomination Checks**
2. **Customer ETA Stock Survival Hazard Modeling**
3. **Multi-Dimensional Bayesian Trust Shrinkage**
4. **Value of Information (VoI) Dispatch Optimization**
5. **TorobChat Retrieval-Augmented Generation (RAG)**

---

## 2. Mathematical Formulations

### A) Leave-One-Out Peer Median (Price Reasonableness)
To evaluate listed prices without introducing self-bias from the target store:

```math
\tilde{P}_{-i} = \operatorname{Median}\left(\{P_j : j \in \mathcal{S}_{\mathrm{peer}}, j \neq i\}\right)
```

- When $|P_i - \tilde{P}\_{-i}| \approx 9 \times P_i$ or $P_i / \tilde{P}\_{-i} \in [9.5, 10.5]$ or $[0.095, 0.105]$, an automated 10x currency discrepancy (Rials instead of Tomans) is detected.

### B) Stock Arrival Hazard Model
In-person shopping depends on transit time. Stock survival at customer arrival is computed as:

```math
S(t_{\mathrm{ETA}}) = P(T > t_{\mathrm{ETA}}) = \exp(-\lambda \cdot t_{\mathrm{ETA}})
```

Where:
- $t\_{\mathrm{ETA}}$ is customer arrival time in minutes.
- The departure rate $\lambda$ is parameterized by item popularity and store sales velocity:

```math
\lambda = \lambda_0 \cdot \gamma_{\mathrm{popularity}} \cdot \gamma_{\mathrm{store\_velocity}}
```

### C) Bayesian Beta-Binomial Store Trust
Store reliability $\theta$ is modeled with a conjugate $\operatorname{Beta}(\alpha\_0, \beta\_0)$ prior. After observing $n$ inquiries with $k$ verified responses:

```math
\alpha_{\mathrm{new}} = \alpha_{\mathrm{old}} \cdot e^{-\Delta t / \tau} + k
```

```math
\beta_{\mathrm{new}} = \beta_{\mathrm{old}} \cdot e^{-\Delta t / \tau} + (n - k)
```

```math
\hat{\theta} = \frac{\alpha_{\mathrm{new}}}{\alpha_{\mathrm{new}} + \beta_{\mathrm{new}}}
```

The time-decay factor $e^{-\Delta t / \tau}$ ensures that recent merchant behavior holds higher predictive power than stale interactions.

### D) Value of Information (VoI) Dispatch Policy
Dispatching notifications or voice calls incurs an interruption cost. Inquiries are dispatched strictly when:

```math
\mathrm{VoI} = \Delta \mathrm{Certainty} \times \mathrm{TransactionValue} - \mathrm{InterruptionCost} > 0
```

---

## 3. Technology Stack

- **Framework**: Python 3.11+ · [FastAPI](https://fastapi.tiangolo.com/) · Uvicorn
- **Analytical Storage**: [DuckDB](https://duckdb.org/) for sub-millisecond columnar queries across 225k products and 6.4k physical stores
- **Transaction Ledger**: SQLite in Write-Ahead Logging (WAL) mode for idempotent inquiry state transitions
- **Validation**: Pydantic v2 with automated OpenAPI v3 generation
- **LLM Integration**: OpenAI-compatible Google Gemini endpoint for TorobChat consultation

---

## 4. Local Execution & Testing

```bash
cd torob
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run server with live reload:
uvicorn torob.api.main:app --host 0.0.0.0 --port 8080 --reload
```
- Interactive Swagger Docs: `http://localhost:8080/docs`
- Redoc Documentation: `http://localhost:8080/redoc`

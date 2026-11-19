# 🎬 Interactive Pitch Deck & Hackathon Presentation

<p align="center">
  <b>🌐 Language / زبان:</b>
  <a href="PRESENTATION.md"><b> 🇮🇷 فارسی</b></a> |
  <a href="PRESENTATION_EN.md"><b> 🇬🇧 English (Current)</b></a>
</p>

---

> This document details the 17-slide interactive pitch deck, synchronized dual-phone demo videos, and speech script in [`presentation/`](../presentation/).

---

## 1. Key Presentation Features

- **Tech Stack**: HTML5, Tailwind CSS, lightweight JavaScript with zero external CDN dependencies (100% offline self-contained).
- **Structure**:
  - **Part 1 (Slides 1 – 8)**: The in-person shopping dilemma, competitive gaps, value proposition, and the live product demo.
  - **Part 2 (Slides 9 – 17)**: System architecture, mathematical models (stock survival, Bayesian shrinkage, VoI), scalability, and commercial roadmap.
- **Synchronized Video Assets**: Real synchronized screen recordings showing the shopper sending an inquiry on the web app and the merchant's phone ringing simultaneously.
- **Complete Speech Script**: Comprehensive speaker script provided in [`presentation/SCRIPT.md`](../presentation/SCRIPT.md).

---

## 2. Running Locally

```bash
cd presentation
python3 -m http.server 8000
```
Open your browser at `http://localhost:8000`.

### Navigation Shortcuts:
- `Right Arrow` or `Space`: Next slide
- `Left Arrow`: Previous slide
- `F`: Toggle Fullscreen mode

# TorobMap Presentation (Hackathon)

A single-page HTML presentation with no installation required and no internet access needed (fonts and video are inside the folder).

## Running It

Open `index.html` in Chrome/Edge (double-clicking is enough).

| Key                                         | Action          |
| ------------------------------------------- | --------------- |
| `←` / Space / Enter                         | Next slide      |
| `→` / Backspace                             | Previous slide  |
| `F`                                         | Fullscreen      |
| `Home` / `End`                              | First / Last    |
| Tap / Click on the two halves of the screen | Next / Previous |

The page automatically scales to any screen size (1920×1080). For the demo video, put the browser in fullscreen and record the screen.

## Structure (17 Slides)

**Part 1 · What We Built (12 slides, more important):** Title ← Problem ← Four Challenge Steps ← TorobChat ← List & Comparison ← Map ← Information Transparency ← Inquiry System (Diagram) ← "One Inquiry, Two Phones" ← Seller App (Phone Rings) ← **Live Demo on Two Phones** ← Jimbo & Deployment.
**Part 2 · System Design (5 slides, summary):** Architecture ← Inventory Algorithm ← Inquiry Method ← Pricing & Trust ← Summary.

Narration script for video recording: [`SCRIPT.md`](SCRIPT.md)

## Live Demo (Slide 11)

The customer's phone video (`assets/mobile/app-demo.mp4`) and the seller's phone are synchronized: timestamps are in `assets/mobile/timeline.json`, and the seller's phone rings at the moment of the inquiry, then shows the response form and at the end displays "Response Sent". The video was recorded with a real server; the seller's response was submitted using the same Android app API (the seller's phone image is a real photo of the app).

## Rebuilding Video and Images (Optional)

With the backend (port 8080) and web app (port 3000) running:

```bash
cd tools && npm install
node record-mobile.js ../assets/mobile    # record mobile flow + screenshots + timeline.json
node deckshots.js                         # capture all slides in assets/deck

```

Then crop the video and convert it to MP4 (command from work history: `crop=390:844:0:0,scale=780:1688`).

## Seller App Images

From `../merchentappimages/NOTES.md` — most important ones: the "Phone Rings" screen (`12-URGENT-CALL-incoming`), rejection reason, response form.

> Before presenting: images `05/07/08` have real names and numbers and are **not used** in the slides.

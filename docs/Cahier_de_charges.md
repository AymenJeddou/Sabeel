# Pothole Detection & Management System — Tunisia
## Simple Version (v4.0)

A mobile app, a small AI model, a map, and a simple RAG agent

**Authors:** Aymen Jeddou, Tharaa Oueslati, Jasseur Chibani, Jed Belhaj Mohamed
**Date:** September 2026
**Project length:** 4 weeks, 0 TND hardware budget
**Cloud services:** Google Cloud Run, Hugging Face, OpenStreetMap, Supabase
**Who reads this:** Municipalities, DGPC, Ministry of Equipment and Housing

This version uses plain language and a plain black-and-white layout. It adds, for every technology choice, a table comparing candidates with checks and crosses, plus a simple component diagram for the microservices.

---

## Contents
1. Background
2. Goals and Targets
3. Features and User Stories
4. Use Case Diagram
5. What Each Actor Gets
6. Non-Functional Requirements
7. How It Is Built
8. Data and Privacy
9. Team — 4 Roles
10. 4-Week Plan
11. Risks and Fixes
12. Final Checklist
13. Appendices

---

## 1. Background

### 1.1 The problem

Tunisia has about 20,000 km of classified roads (national, regional, local), plus thousands more kilometres of city streets. The roads break down fast for three reasons:

- **Heat.** Very hot summers (over 45°C) followed by heavy autumn rain make the road surface crack.
- **Water.** Water goes into the cracks and weakens the ground under the road. Then a pothole appears within days.
- **Slow reporting.** Today, people report potholes by phone call, letter, or social media. There is no shared format, no exact location, and no way to track what happens next.

> **Why:** A pothole that is fixed early costs much less than one left for months. Waiting a week to report it can mean the road needs a full rebuild instead of a quick patch. So the fastest way to save money is to shorten the time between "pothole appears" and "repair order sent." That is what this project does.

### 1.2 Who uses this

| Actor | Role | What they want |
|---|---|---|
| Citizen / driver | Sees the pothole first | Report it in under 15 seconds, no account needed |
| Municipality (baladiya) | Manages city streets | Clear, ready-to-use work sheets |
| DGPC | Manages national/regional roads | One combined view by road and by region |
| Ministry of Equipment | Plans and pays for road work | Combined data to plan the budget |
| Engineering team | Builds the MVP | A working demo in 4 weeks, at no cost |

### 1.3 What already exists

Three kinds of solutions exist today: (a) special survey cars with cameras — accurate but expensive; (b) normal complaint apps — cheap but no automatic grading; (c) research projects that detect potholes with AI — good at detection but stop there, they do not create a repair order.

> **Why:** This project mixes all three: cheap reporting like (b), automatic grading like (c), and it goes one step further — it turns a GPS point into a real work sheet using an AI agent that reads the rules. No other tool does that last step.

## 2. Goals and Targets

1. **Capture.** Get a photo (from a citizen) or a video frame (from a driving phone), with GPS, and score it 1 to 5 for severity.
2. **Detect.** Use a free, open AI model (YOLOv8n) that runs on a normal CPU, no GPU needed.
3. **Write the sheet.** Use a RAG agent to turn a confirmed serious pothole into a work order, based on the real rules.
4. **Show the map.** Combine all reports on one live map, removing duplicates and sorting by priority.

| What we measure | Target | Where |
|---|---|---|
| Model accuracy (mAP@50) | ≥ 0.75 | Test images |
| Detection speed | < 250 ms | One photo, on Cloud Run |
| Time to report (open app to done) | < 15 s | Real test |
| Sheets rated "ready to use" | ≥ 90% | Human check |
| Distance to count two reports as one | < 5 m | In the database |
| Driving mode running time | ≥ 20 min | Phone as dashcam |
| Monthly server cost | 0 TND | Free plans only |

> **Why:** 0.75 accuracy is the point where the model becomes useful as a filter — below that, too many wrong detections need human checking. Under 250 ms keeps a request cheap on the free server plan. Under 15 seconds is about how long someone will stand at a pothole to report it. 5 metres matches how accurate a phone's GPS usually is in a city.

## 3. Features and User Stories

Six features, F1 to F6. Each one has a short story, a rule, and a way to check it works.

### 3.1 F1 — Take a photo and report it

*I see a pothole. I take a photo. I want the app to find my exact spot and grade the pothole, without me typing anything.*

When the photo is taken, the app sends: the photo, GPS position (with accuracy), time, direction, and speed. A small AI model checks the photo and gives a score from 1 to 5.

> **Why:** Speed matters — above about 40 km/h a photo from a moving car is too blurry, so we mark it "to check" instead of rejecting it. Direction tells us which side of the road the pothole is on.

**Severity scale (1 to 5)**

| Score | What it looks like | Color | What happens |
|---|---|---|---|
| 1 – small | Small crack or hole under 25mm deep | Green | Just counted, no sheet |
| 2 – low | Hole 25–50mm | Green | Counted, alert if many nearby |
| 3 – medium | Hole 50–75mm | Orange | Sheet made if confirmed |
| 4 – high | Hole over 75mm | Orange | Sheet made, plan soon |
| 5 – serious | Deep hole, real danger | Red | Sheet made now, urgent |

**How we check it works.** The photo and location are sent together; if there is no GPS permission, the app explains why it is needed; the score is a whole number 1 to 5 with a confidence value; with no internet, the report waits on the phone and sends later.

### 3.2 F2 — Map with filters

*As a city officer, I want to open a map and see the bad spots at once, without seeing the same pothole twice.*

Full-screen map (OpenStreetMap). Each pothole is a colored dot. If two reports are less than 5 metres apart, the pothole moves from "new" to "confirmed."

> **Why:** One report alone can be a mistake, a wrong AI guess, or a puddle. Two reports close together make it much more likely the pothole is real, without needing a human to check every single one.

**How we check it works.** Filters by score, by state, by region; the match check runs in the database, not on the phone; tapping a dot shows the full record; the map stays smooth with 5,000+ dots grouped by zoom level.

### 3.3 F3 — Write the work sheet (RAG)

*As a technical manager, I want a confirmed serious pothole to turn into a real work order, sent to the right office, with the rules quoted.*

When a pothole scores 3 to 5 and is confirmed, the system: (1) finds which road type it is on; (2) looks up the matching rules in a small text database; (3) gives those rules to an AI model, which writes the sheet — what is wrong, how big it is, how urgent, how to fix it, who should get it, and which rule it is based on.

> **Why:** A fixed template cannot adapt to the road type or quote the right rule. An AI model on its own can make up a rule that does not exist — not good enough for an official document. RAG forces the AI to only use real text it was given, and every line can be traced back to its source.

```
GPS + score -> find road type -> look up rules (top 5 matches)
  -> build a prompt with those rules -> free AI model writes the sheet
  -> sheet saved -> sent to the right office -> map shows "sheet sent"
```

**How we check it works.** Every sheet quotes at least one real source; the office it is sent to is never empty; running it twice gives the same result; a sheet is ready in under 20 seconds.

### 3.4 F4 — Priority list and status

*As a city, I want a sorted list of what is mine to fix, and a button to mark it done.*

A list next to the map: each office sees only its own potholes, sorted by urgency × traffic × age. Each row shows the sheet and a "fixed" button.

> **Why:** Without a fixed state, the map would just keep filling up and become useless. The status history also lets us measure how fast each office fixes things.

**How we check it works.** Every status change is time-stamped and can be undone; the sort order updates right away; the list can be saved as CSV or GeoJSON.

### 3.5 F5 — Tell the citizen what happened

*As a driver, I want to know my report was seen, and if it was fixed.*

No account needed. The app keeps the ID of reports made on that phone and shows their state. A small notification appears when a report is marked fixed.

> **Why:** All the data here is given for free by citizens. The only reason people keep reporting is proof that it works. This small feedback loop is what keeps people using the app.

### 3.6 F6 — Hands-free mode while driving

*As a driver, I want to put my phone on the windscreen and drive. The app should find and report potholes on its own.*

The app checks the camera 12 times per second, runs the same AI model on each picture, and makes a report by itself when a pothole is seen clearly on 3 pictures in a row. GPS, speed, and direction are attached each time.

> **Why:** One driver covers many kilometres in one trip, far more than one citizen who stops to take a photo. Because F6 reuses the same AI model and the same server, it is cheap to add — most of the work is on the phone side only.

**Rules.** 12 pictures per second; needs 3 pictures in a row to count; empty pictures (no pothole) are thrown away right on the phone; duplicate reports are merged the same way as F2; capture stops when the car is not moving; capture stops above 80 km/h.

**How we check it works.** Runs 20+ minutes without a crash; only confirmed pictures are uploaded; F6 reports appear on the same map as F1 reports.

### 3.7 What we are not building yet

- Accounts, profiles, points, leaderboards.
- A real dashcam device (only a phone on the windscreen for now).
- A direct link into city computer systems (we only export files for now).
- Automatic cost estimates for repairs.
- A store-published app (an APK file is enough for the demo).

> **Why:** Each of these is its own project. Leaving them out keeps the 4-week plan realistic and lets the team focus on the one new idea: photo → sheet → map, in one chain.

## 4. Use Case Diagram

Five people use the system directly. A sixth actor is the system itself: it starts the work-sheet action on its own, when a pothole becomes confirmed and serious — no person clicks a button for that step.

**Actors:** Citizen, Volunteer driver, Municipality officer, DGPC officer, Ministry analyst, System (auto)

**Actions:**
- Submit pothole report (photo)
- Run hands-free dashcam detection
- Track own report status
- View national dashboard
- View map & filters
- View priority list
- Update status
- Export data (CSV / GeoJSON)
- Write work sheet (RAG) — «include», only if score ≥ 3

**Notes.** "Submit report" and "Update status" both lead to "Write work sheet," but only when the score is 3 or more and the report is confirmed — no person ever clicks "write sheet" directly. "Track own report status" is shared by citizens and volunteer drivers, since a dashcam report belongs to the driver's phone just like a manual photo does.

## 5. What Each Actor Gets

### 5.1 Quick table

| Actor | Main value | Features |
|---|---|---|
| Citizen / driver | Easy reporting + proof it works | F1, F5, F6 |
| Municipality | Ready-to-use, sorted, quoted sheets | F2, F3, F4 |
| DGPC | One combined view of classified roads | F2, F3, F4 |
| Ministry | Combined data for budget decisions | F2, F4 + exports |
| Engineering team | Working demo in 4 weeks, no cost | Full build + CI/CD |

### 5.2 Citizen / road user

- Fast report (F1): photo, GPS, speed, and score in one step, under 15 seconds.
- No account, no personal data stored, report tied only to the phone.
- Offline queue: reports wait on the phone and send later.
- Hands-free dashcam mode (F6).
- Sees the status of their own reports (F5).
- Gets a thank-you message when a pothole is fixed.
- Sees the new report on the map right away.

### 5.3 Municipality / Baladiya

- Work sheets (F3) for confirmed potholes on city streets, with the rule quoted.
- A sorted list of what is theirs to fix (F4).
- The map with filters and duplicate removal (F2).
- Full status history: new → confirmed → sheet sent → fixed.
- Export to CSV / GeoJSON for their own planning.
- Automatic routing so city-street reports go to the right office.
- A measure of how fast they fix things.

### 5.4 DGPC

- One combined map of national and regional roads.
- Automatic routing of sheets to the right regional office.
- Sorted lists per office.
- Full history and audit trail.
- Export for planning by road or by region.
- A measure of repair speed on the classified network.

### 5.5 Ministry of Equipment

- One national, combined, duplicate-free dataset.
- Repair-speed numbers by office, region, and road type.
- Density and severity charts, for budget decisions.
- A traceable set of sheets, showing real need.
- A pipeline that costs nothing extra to run.
- A history of closed cases, for future planning.

### 5.6 Engineering team

- A simple, scale-to-zero setup that stays free.
- Clear handoffs between the 4 roles.
- Automatic build and deploy (CI/CD).
- Auto-made API docs, health check, and logs.
- A repeatable AI training process.
- A clear "not doing this yet" list and risk list.
- A final checklist (9 items) to prove the demo works.

### 5.7 Rules for the whole MVP

- No accounts, profiles, points, or leaderboards.
- Dashcam mode only on a phone, no special hardware.
- City systems get data only through file export for now.
- No automatic cost estimate.
- An APK file is enough, no app store needed.
- All servers stay on free plans.

## 6. Non-Functional Requirements

| Area | Requirement | Target | Why |
|---|---|---|---|
| Speed | Full report round trip | < 3 s (no RAG) | Feels instant to the citizen |
| Uptime | OK with cold start | < 4 s first call | Free server trade-off |
| Growth | Auto scale up | 0 to 80 copies | Spikes after storms |
| Cost | Stay on free plans | 0 TND/month | Main rule of the project |
| Safety | HTTPS, rate limits, checks | 100% of routes | No login means more checks needed |
| Privacy | No personal data; blur faces/plates | Before saving | Follows Law 2004-63 |
| Reuse | One Dockerfile, no lock-in | 1 file | Easy to move or teach later |
| Tracking | Logs + numbers per request | Always on | Easy to debug |
| Access | Good contrast, big buttons | WCAG 2.1 AA | Used outdoors, in the sun |
| Language | English/French, Arabic-ready | All text external | Tunisian users |
| Battery (F6) | Keeps working without draining the phone | 20+ min | Driving mode should not overheat the phone |

## 7. How It Is Built

### 7.1 Big picture

No GPU, no server running all the time, no paid plan. Everything runs in small containers that turn off when nobody is using them. This keeps it simple enough for 4 people to finish in 4 weeks.

```
[Phone app] photo/frame + GPS -> [API on Cloud Run]
  -> AI model checks photo -> score
  -> [Supabase] save + check for nearby duplicates
  -> if score>=3 & confirmed: background task -> RAG agent -> text database (top 5)
  -> free AI model -> sheet

[Phone app / map] <- map data <- [API] <- [Supabase]

F6 driving mode: pictures checked on the phone, only confirmed ones uploaded

Build & deploy: [GitHub Actions] build -> [image storage] -> [Cloud Run] (auto, on push to main)
```

> **Why:** Two things are kept simple on purpose: (1) duplicate checking runs as one quick database query right when a report comes in, instead of a separate batch job — fast enough at MVP size and one less moving part; (2) the RAG step runs as a background task built into the API, instead of a separate queue system — nothing extra to set up or pay for, and still fast enough (20s target).

### 7.2 Component diagram (microservices)

Three real services sit behind the API: the vision model, the RAG agent, and the core API that ties everything together.

```
Phone app (Flutter) — photo, map, offline queue
        │
        ▼
Core API — reports, map, status (FastAPI)
        │
   ┌────┴─────┐
   ▼          ▼
Vision service          RAG service
(YOLOv8n, ONNX)          (looks up rules, writes sheet)
   │                         │
   ▼                         ▼
Supabase                 Text database
(reports, status, photos) (rules, Chroma)
```

**Note.** During the 4-week build, all 3 services run inside one container (one Dockerfile, one deploy). This picture shows the logical split, not the deploy setup. Splitting them into real separate services later is possible without a redesign, because the API calls between them are already function calls with a fixed input and output.

### 7.3 Step-by-step build plan

**1. Phone app (Flutter) — Role 4**
1. Use `camera` (photo + video), `geolocator` (GPS), `connectivity_plus` (online check), `hive` (offline queue), `flutter_map` (OSM map), `dio` (send files to the API).
2. Capture screen (F1): take photo → read GPS, direction, speed → send to `POST /reports` → if it fails or there is no internet, save it to the phone and send later.
3. Map screen (F2): show OSM tiles, load dots from `GET /map`, color by score; tap a dot to see the photo, history, and sheet.
4. F6 mode: read the camera stream, keep about 1 picture per second, skip pictures if speed is above 80 km/h or the car is stopped, send only confirmed ones.
5. F5: save report IDs on the phone, check their status, show a small notification when one is fixed.
6. Build a debug/release APK, no store needed for the demo.

**2. AI model (Vision) — Role 1**
1. Photos (days 1–3): combine a free Roboflow/Kaggle pothole dataset with team photos from Tunisia. Aim for 2,000+ pictures, split 70/15/15, by area (not random) so the test set is fair.
2. Labels: use Roboflow's auto-label helper, then check by hand.
3. Extra pictures: add blur, rain, shadow, and brightness changes so the model learns real conditions.
4. Training (free Colab GPU): `yolo train model=yolov8n.pt data=data.yaml epochs=60 imgsz=640`
5. Export: `yolo export model=best.pt format=onnx opset=12`, then shrink it with `quantize_dynamic`.
6. Use it: one function `infer(image) -> {boxes, score, confidence}` using ONNX Runtime (CPU only).
7. Score rule: bigger box in the photo means higher score, based on the severity table (3.1).

**3. RAG agent — Role 2**
1. Rules (days 1–4): collect the road-type rules and the law about who manages what (15–30 pages is enough).
2. Split into chunks: 400 characters each, 50 characters overlap, keep the title and section for each chunk.
3. Turn text into numbers: a free multilingual model (works for French too).
4. Store: Chroma, saved on disk, no extra service needed.
5. Look up: take the top 5 matching chunks for a given road type and score.
6. Write the prompt: force the AI to quote a chunk id for every claim, and to say "not enough rules" if nothing matches well.
7. Call the AI: free Hugging Face model (Qwen or Llama); if the answer is not valid, fall back to a simple template.

**4. Core API — Role 3**
1. Database: Supabase with PostGIS on. Tables: `reports`, `report_events` (history), `sheets`.
2. `POST /reports`: save photo → check the AI score → save the row → check for a nearby report (5m) → if confirmed and score ≥3, start the RAG step in the background.
3. `GET /map`: return the dots that match the current view and filters, as GeoJSON.
4. `PATCH /reports/{id}`: change status in order only (no skipping steps), and log every change.
5. Safety: rate limits and strict input checks on every route, since there is no login.

**5. Build & deploy — Role 4**
1. One small Dockerfile, built in two steps to keep it light.
2. On every push: check code style, run tests, build the image.
3. On push to main: deploy straight to Cloud Run.
4. A `/health` route, pinged every 10 minutes by a free tool, so the demo does not feel slow on the first request.

### 7.4 Technology choices

For each choice: the real options (candidates), what each can do (✓/✗), and the winner.

**1. Mobile app framework** — *Constraint: one month, small team, must run on Android and iPhone.*

| Criteria | Flutter | React Native | Native (2 apps) |
|---|---|---|---|
| One codebase for both phones | ✓ | ✓ | ✗ |
| Good, free map drawing | ✓ | ✗ | ✗ |
| Easy for the team to learn fast | ✓ | ✗ | ✗ |

**Winner: Flutter.** One codebase, good maps, and the fastest to learn in a month.

**2. Map base layer** — *Constraint: 0 TND, must cover Tunisia well.*

| Criteria | OpenStreetMap | Google Maps | Mapbox |
|---|---|---|---|
| Free, no key needed | ✓ | ✗ | ✗ |
| No usage limit | ✓ | ✗ | ✗ |
| Covers Tunisia well | ✓ | ✓ | ✓ |

**Winner: OpenStreetMap.** Totally free and no key to manage.

**3. Detection model** — *Constraint: must run on CPU, under 250ms.*

| Criteria | YOLOv8n | YOLOv8s/m | Faster R-CNN |
|---|---|---|---|
| Fast enough on CPU | ✓ | ✗ | ✗ |
| Small file size | ✓ | ✗ | ✗ |
| Good enough accuracy | ✓ | ✓ | ✓ |

**Winner: YOLOv8n.** The smallest version that still meets the speed target.

**4. Model file format** — *Constraint: no GPU available on the server.*

| Criteria | ONNX | PyTorch (.pt) | TensorRT |
|---|---|---|---|
| Runs well on CPU only | ✓ | ✓ | ✗ |
| Small, easy to move | ✓ | ✗ | ✗ |
| No GPU needed to run | ✓ | ✓ | ✗ |

**Winner: ONNX.** Light, portable, and does not need PyTorch in production.

**5. Text database (vector store)** — *Constraint: 0 TND, small set of rules (15–30 pages).*

| Criteria | Chroma (local) | Pinecone | Weaviate |
|---|---|---|---|
| Free, no extra account | ✓ | ✗ | ✗ |
| Fits in the API container | ✓ | ✗ | ✗ |
| Fast enough at this size | ✓ | ✓ | ✓ |

**Winner: Chroma.** The data is small enough to live right inside the API, no extra service.

**6. Turning rules into numbers (embeddings)** — *Constraint: must understand French text, 0 TND.*

| Criteria | Multilingual SentenceTransformers | OpenAI embeddings | Cohere embeddings |
|---|---|---|---|
| Free, runs on our own machine | ✓ | ✗ | ✗ |
| Understands French | ✓ | ✓ | ✓ |
| No cost per request | ✓ | ✗ | ✗ |

**Winner: Multilingual SentenceTransformers.** Free, local, and handles French text.

**7. AI model that writes the sheet (LLM)** — *Constraint: 0 TND, no GPU to host it ourselves.*

| Criteria | Qwen 2.5 / Llama 3.2 | GPT-4o | Claude |
|---|---|---|---|
| Free to call | ✓ | ✗ | ✗ |
| Open weights | ✓ | ✗ | ✗ |
| No monthly bill | ✓ | ✗ | ✗ |

**Winner: Qwen 2.5 / Llama 3.2 (Hugging Face).** Free API, open weights, no GPU to manage.

**8. API framework** — *Constraint: needs to handle uploads and AI calls without blocking.*

| Criteria | FastAPI | Flask | Django REST |
|---|---|---|---|
| Handles many requests at once | ✓ | ✗ | ✗ |
| Auto-builds API docs | ✓ | ✗ | ✓ |
| Checks input automatically | ✓ | ✗ | ✓ |

**Winner: FastAPI.** Built for async work, and gives us the API docs for free.

**9. Database** — *Constraint: needs to search what is near this point.*

| Criteria | Supabase (PostGIS) | MongoDB | Firebase |
|---|---|---|---|
| Built-in map/location search | ✓ | ✗ | ✗ |
| Free tier is big enough | ✓ | ✓ | ✓ |
| Standard SQL, easy to learn | ✓ | ✗ | ✗ |

**Winner: Supabase (PostGIS).** Location search comes built in, no extra code needed.

**10. Background job handling** — *Constraint: low traffic during the demo month.*

| Criteria | FastAPI BackgroundTasks | Celery | Google Pub/Sub |
|---|---|---|---|
| No extra service to run | ✓ | ✗ | ✗ |
| Free | ✓ | ✓ | ✓ |
| Simple to set up in a month | ✓ | ✗ | ✗ |

**Winner: FastAPI BackgroundTasks.** Nothing extra to deploy, and fast enough for MVP traffic.

**11. Where the app runs (compute)** — *Constraint: 0 TND, traffic is low most of the time.*

| Criteria | Google Cloud Run | Normal server (VM) | Kubernetes |
|---|---|---|---|
| Free when nobody is using it | ✓ | ✗ | ✗ |
| No server to manage | ✓ | ✗ | ✗ |
| Scales up on its own | ✓ | ✗ | ✓ |

**Winner: Google Cloud Run.** Costs nothing while idle, which is most of the time.

**12. Build & deploy tool (CI/CD)** — *Constraint: small team, already using GitHub.*

| Criteria | GitHub Actions | Jenkins | GitLab CI (self-host) |
|---|---|---|---|
| Free build minutes | ✓ | ✗ | ✗ |
| Works right inside GitHub | ✓ | ✗ | ✗ |
| No server to maintain | ✓ | ✗ | ✗ |

**Winner: GitHub Actions.** Built into the repo we already use, and free.

**13. Driving-mode hardware (F6)** — *Constraint: 0 TND hardware budget.*

| Criteria | Phone on windscreen | Dedicated dashcam |
|---|---|---|
| No extra cost | ✓ | ✗ |
| Reuses the same app and AI model | ✓ | ✗ |
| Easy for any volunteer to use | ✓ | ✗ |

**Winner: Phone on windscreen.** Free, and uses the exact same code as F1.

### 7.5 Server cost check (demo month)

| Service | Free limit / month | What we expect to use | Room left |
|---|---|---|---|
| Cloud Run (requests) | 2,000,000 | ~15,000 | > 99% |
| Cloud Run (compute time) | 180,000 vCPU·s | ~4,500 | ~97% |
| Supabase (storage) | 500 MB | < 50 MB | > 90% |
| Hugging Face API | shared limit | ~500 sheets | background task |
| GitHub Actions | 2,000 min | ~200 min | ~90% |

## 8. Data and Privacy

### 8.1 Photos for training

Sources: free datasets (Roboflow, Kaggle), plus real team photos and driving clips from Tunisia. Target: 2,000+ photos, split 70/15/15 by area (not randomly), so the test set is fair. One label only: "pothole." The severity score is not labeled by hand — it is worked out from the size of the box.

### 8.2 Rules for the RAG agent

The text database holds: which road type is which (national/regional/local/city); who manages what (Local Authorities Code, Law 2018-29); how to repair a pothole (patching methods, when to use each one); and any standard numbers that apply.

> **Why:** Text is split into small pieces (300–500 characters, with overlap) and stored with its title and section. Every sheet keeps the list of pieces it used, so we can check it and fix the rule set, not the AI model, if something is wrong.

### 8.3 Keeping people's data safe

- No name, no phone number, no account ID is ever collected. The report is linked only to the phone.
- Faces and license plates are blurred automatically before a photo is saved on the server.
- Follows Law 2004-63 on personal data. Location data is about the road, not a person's daily trip.
- Raw photos are deleted once the sheet is made. Only the summary data and the sheet stay.

## 9. Team — 4 Roles

Four people, four clear jobs, connected by a fixed set of inputs and outputs so everyone can work at the same time.

### 9.1 Role 1 — AI model (ML Engineer)

Build the photo set, train and export the model, decide the severity rule, check speed on CPU.
**Delivers:** `pothole_model.onnx` + the code to run it + a short report.

### 9.2 Role 2 — RAG agent (AI/RAG Specialist)

Collect and split the rules, build the text database, write the prompt, add safety checks (must quote a source, must say "not sure" if unsure).
**Delivers:** `rag_agent.py` + the saved text database.

### 9.3 Role 3 — Core API (Backend Engineer)

Build the API, set up the database, write the duplicate check, connect the AI model and RAG agent.
**Delivers:** the API with auto-made docs + the database setup.

### 9.4 Role 4 — App and deploy (Full-Stack & DevOps)

Build the phone app, the map, the offline queue, the driving mode; set up the Dockerfile and the auto-deploy pipeline.
**Delivers:** the working app + the auto-deploy setup.

### 9.5 Fixed handoffs between roles

| Between | From → to | Fixed input/output |
|---|---|---|
| AI model | Role 1 → Role 3, 4 | `infer(image) -> {boxes, score, confidence}` |
| RAG | Role 2 → Role 3 | `generate(lat, lon, score) -> sheet` |
| API | Role 3 → Role 4 | `POST /reports`, `GET /map`, `GET /reports/{id}`, `PATCH /reports/{id}` |
| Deploy | Role 4 → all | One container, clear list of settings, a live test link |

## 10. 4-Week Plan

| Week | What gets done | Check before moving on |
|---|---|---|
| W1 | Photo set started, first model training; rules collected, text database started; API design fixed. | Accuracy ≥ 0.6 on test set; the text search returns real, quoted rules. |
| W2 | API connects the AI model and RAG; database live with duplicate check; API docs online; sheet generation running in background. | A real photo makes a real, located report; a confirmed serious pothole makes a sheet. |
| W3 | Phone app (capture, GPS, offline queue); map connected to the API; priority list and feedback loop; driving mode tested. | Full flow works on a phone: photo → dot on map → readable sheet. Accuracy ≥ 0.75. |
| W4 | Auto-deploy live; full tests; final numbers checked; safety checks added; demo ready. | Every target in Section 2 is measured; the live demo works on Cloud Run. |

## 11. Risks and Fixes

| Risk | Chance | Impact | Fix |
|---|---|---|---|
| Not enough photos → low accuracy | Med | High | Start collecting photos on day 1, add fake variety, start from a pretrained model |
| Hugging Face limit or outage | Med | Med | Retry in background; fall back to a smaller model; save old sheets |
| Slow first request (cold start) | High | Low | Ping the server before the demo; show a loading message |
| Wrong GPS in the city | High | Med | Use GPS accuracy value, require 2 nearby reports, use direction to pick the right road side |
| F6: blurry pictures at speed | High | Med | Lower frame rate, need 3 in a row, stop above 80 km/h, train with blurry photos too |
| F6: privacy risk from constant capture | Med | Med | Throw away empty pictures on the phone, blur faces/plates, no full trip saved |
| Rule set is incomplete | Med | Med | Keep the rule set small and clear about what it covers |
| Free storage limit reached | Low | Med | Delete raw photos after the sheet is made |
| Scope creep (adding new features) | High | Med | Section 3.7 is the limit; new ideas go on a later list |
| Wrong AI guesses (puddle, shadow) | Med | Med | Require 2 nearby reports, use a confidence limit, train with "not a pothole" photos too |

## 12. Final Checklist

The MVP is done when all of this works, shown live to the team and supervisors:

1. A real photo makes a colored dot on the map in under 3 seconds (not counting the sheet).
2. A short drive with a phone on the windscreen makes at least one correct report by itself.
3. The model reaches 0.75+ accuracy on the test set, with a report to prove it.
4. A confirmed serious pothole makes a sheet that quotes a real rule and has a real office to send to.
5. The map shows, filters, and removes duplicate reports; the check runs in the database.
6. The status flow (new → confirmed → sheet sent → fixed) works and is logged.
7. Every push to main deploys to Cloud Run by itself, and it works.
8. The monthly server cost is 0 TND.
9. The repo has: all 4 parts' code, the Dockerfile, the API docs, a README, the model report, this checklist.

## 13. Appendices

### Appendix A — Word list

| Word | Meaning |
|---|---|
| Pothole | A hole in the road surface. |
| Open model (open-weight) | A free AI model anyone can download and use, no paid license needed. |
| RAG | An AI method that must quote real text instead of making things up. |
| mAP@50 | A number that shows how good the AI model is at finding potholes. |
| ONNX | A file format that lets an AI model run fast on a normal CPU. |
| Duplicate check | Looking for another report close by (under 5 m) to confirm a pothole is real. |
| Scale-to-zero | The server turns off and costs nothing when nobody is using it. |
| Cold start | The short delay the first time a server wakes up after being off. |
| Dashcam mode | Using a phone on the windscreen to find potholes while driving. |
| Baladiya | A Tunisian city or town government. |

### Appendix B — Road types

| Type | Code | Who manages it | Who gets the sheet |
|---|---|---|---|
| National road | RN | DGPC / Ministry of Equipment | The right regional office |
| Regional road | RR | DGPC / regional office | The right regional office |
| Local road (classified) | RL | Regional office or city, depends on the section | Regional office or city |
| City street (unclassified) | — | The city (baladiya) | The city's technical service |
| Motorway | A | Tunisie Autoroutes | Not part of this MVP |

### Appendix C — API routes

| Route | Description |
|---|---|
| `POST /reports` | New report (photo + lat + lon + speed + direction + time + source) |
| `GET /reports/{id}` | Full record (photos, history, road, sheet) |
| `PATCH /reports/{id}` | Change status (confirmed / sheet sent / fixed) + note |
| `GET /map?bbox=&sev=&state=` | Map data for the current view |
| `GET /authorities/{id}/queue` | Sorted list for one office (F4) |
| `GET /export?format=geojson\|csv` | Download filtered data |
| `GET /health` | Check the server is awake |
| `GET /docs` | Auto-made API docs |

The `source` field on `POST /reports` is `citizen_photo` or `dashcam_frame` (F6), so we can tell the two apart later.

---

*Pothole Detection & Management — simple version — MVP Tunisia.*
*A. Jeddou, T. Oueslati, J. Chibani, J. Belhaj Mohamed — September 2026.*

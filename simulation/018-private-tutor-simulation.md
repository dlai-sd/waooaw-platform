# Simulation 018 — Private Tutor Agent: Parent Hiring + Student Learning

**Type:** End-to-End Simulation — Private Tutor Agent v1.0
**Status:** Active
**Purpose:** Validate the full lifecycle: parent configuration, first student session, ongoing teaching with Learning Intelligence, homework help, parent progress report. Surface gaps not visible in the spec.
**Parent Persona:** Meera Shah, 41, working professional (teacher herself), Pune. Daughter Priya, Class 9 CBSE. Concerned about Maths and Science; paying ₹18,000/year for coaching that gives Priya zero personal attention.
**Student Persona:** Priya Shah, 14, Class 9 CBSE. Shy. Understands concepts but struggles with calculations. Gets nervous when called on. Responds well to encouragement. Has a habit of saying "I know" when she doesn't.

---

## PART A — PARENT: Hiring, Trial, and Configuration

---

### Day 0 — Discovery (Meera sees WAOOAW)

Meera finds WAOOAW through a Facebook ad: *"Professional digital marketing for your dental clinic. ₹1,499/month."* — wrong agent, but she taps the WAOOAW website and sees the tutor offering.

**[GAP-T001] Trial Session Not In Spec**

Meera's first question on the website: **"Can I try one session before subscribing?"**

The spec has no trial mechanism. Every ed-tech company (BYJU's, Vedantu, PW) offers a free demo class. Without a trial, the conversion from "curious parent" to "paying subscriber" depends entirely on the website copy — the parent cannot experience the product before committing ₹499-999/month.

**Resolution needed:**
```yaml
trial_session:
  offering: 1 free session (20 minutes) before first payment
  scope: Skill 0 (Student Profiling / Introduction) — naturally a trial
  constitutional_note: "Trial session creates no STUDENT_PROFILE_ESTABLISHED record
                        until parent converts to paid. Data from trial session deleted
                        if parent does not subscribe within 7 days (C-060 data minimization)"
  parent_sees: the teacher persona, the whiteboard interface, the student's comfort
  conversion_trigger: "At session end — teacher says 'I think we're going to work well
                       together. Your mum can continue from here if you'd like to carry on.'"
```

---

### Day 1 — Parent Configuration (10 minutes, portal)

Meera registers. Platform already knows: Priya, Class 9, CBSE (from registration form).

**Exchange 1:**
> **Platform:** "Welcome Meera! You've registered Priya — Class 9, CBSE. Which subjects would you like Priya to have a tutor for?"

> **Meera:** "All subjects, but especially Maths and Science. She's weak there."

> **Platform records:** subjects = ALL, priority_note = "Maths + Science flagged as priority"
> → Never asks for board or class — already known.

**Exchange 2:**
> **Platform:** "What language should the teacher primarily use with Priya? English only, Hindi with English, Marathi, or another language?"

> **Meera:** "Hindi and English mixed — we speak both at home. We're in Pune."

> **Platform records:** language = HINDI_ENGLISH, regional_context = PUNE_MAHARASHTRA

**Exchange 3:**
> **Platform:** "How would you describe the teacher you want?
> (a) Gentle and encouraging — patient, no pressure
> (b) Warm but expects effort — pushes when needed
> (c) Strict and demanding — high expectations
> 
> And teaching style?"

> **Meera:** "Definitely (b). She responds well to encouragement but she also needs someone who won't let her get away with 'I know' when she clearly doesn't. Mix of story-based and visual — she's a visual learner."

> **Platform records:** strictness = MODERATE, teaching_style = [STORY_BASED, VISUAL, MIXED]
> *Note: "Won't let her get away with 'I know'" → platform flags as specific_instruction*

**Exchange 4:**
> **Platform:** "What would you like Priya to call her teacher?"

> **Meera:** "Sunita Ma'am. It's a familiar name — feels like a real teacher."

> **Platform records:** teacher_name = "Sunita Ma'am"

> **Platform:** "And the personality — which feels right?"

> **Meera:** "Warm but with backbone. Someone who tells stories but also pushes. Like a favourite teacher who you slightly fear but mostly love."

> **Platform records:** personality = [WARM_AND_PATIENT, ENTHUSIASTIC_PASSIONATE, STRICT_BUT_FAIR]

**Exchange 5:**
> **Platform:** "Anything Sunita Ma'am should know about Priya before they meet?"

> **Meera:** "She's very shy — gives one-word answers when nervous. She says 'I know' when she doesn't understand, so the teacher needs to check properly. She's actually quite smart but her calculation speed is slow. Very sensitive — criticism needs to be gentle. She LOVED her Class 7 science teacher Mrs. Kulkarni because she told stories about scientists. That's the vibe I want."

> **Platform records:** specific_instructions verbatim. Flags: shy_student = true, check_understanding_explicitly = true, responds_to_stories = true.

**Progressive Summary:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━
PRIYA'S TEACHER CONFIGURATION
━━━━━━━━━━━━━━━━━━━━━━━━━━
Teacher:    Sunita Ma'am
Subjects:   All (Class 9 CBSE — Maths + Science priority)
Language:   Hindi + English (Pune)
Style:      Story-based + visual + mixed
Strictness: Moderate — warm but won't accept "I know" without checking
Personality: Warm, enthusiastic, firm when needed

Note to teacher: Priya is shy. One-word answers when nervous.
Says "I know" when confused — check understanding with questions,
not "do you understand?" Sensitive — criticism must be gentle.
Loved stories about scientists (Class 7 Mrs. Kulkarni reference).

Schedule: Mon / Wed / Fri — 5:30 PM to 6:15 PM
━━━━━━━━━━━━━━━━━━━━━━━━━━
[Confirm] or [Edit]
```

Meera edits one thing: adds Saturday 10 AM as a makeup slot. Confirms.

Evidence record: `TEACHER_PERSONA_CONFIGURED` ✓

---

### Day 1 Evening — Meera's WhatsApp

> **Platform (WhatsApp):** "Sunita Ma'am is ready for Priya! Your first session — Monday at 5:30 PM — will be a short introduction. No studying, no pressure. Ma'am just wants to meet Priya and understand how she learns best. See you Monday! 📚"

**Constitutional note:** Commercial message goes to Meera (parent). Nothing goes to Priya's phone — C-060 ✓

---

## PART B — STUDENT: First Session

---

### Day 3, Monday 5:30 PM — Skill 0: Introduction Session (20 minutes)

Priya opens the WAOOAW app on the family laptop. She sees a whiteboard and hears a voice.

**[Teacher voice — warm, Hindi, not overly formal]:**
> "Hello Priya! Main hoon Sunita Ma'am. Aaj koi padhai nahi — sirf baat karenge. Theek hai?"
> *(Hello Priya! I'm Sunita Ma'am. Today no studying — we'll just talk. Okay?)*

**Priya (typed, one word):** "okay"

> **Sunita Ma'am:** "Priya, kaunsa subject sabse zyada achha lagta hai tumhe? Aur kaunsa thoda mushkil lagta hai?"
> *(Which subject do you like most? And which feels a bit difficult?)*

**Priya:** "Science thoda achha hai. Maths se dar lagta hai."
*(Science is okay. I'm scared of Maths.)*

> **Sunita Ma'am:** "Dar lagta hai — that's honest. Mujhe batao — kya specifically scary lagta hai? Numbers? Formulas? Ya koi particular chapter?"

**Priya:** "Calculations. Aur algebra mein variables samajh nahi aate."
*(Calculations. And I don't understand variables in algebra.)*

> **Sunita Ma'am:** "Acha — toh concept samajhte ho lekin calculation mein slip hoti hai. That's actually very common and very fixable. Algebra ki baat karo — Variables ko main tumhe ek aise samjhaugi ki life mein use hote hue dekha hoga. Aaj nahi — but soon. Promise."

*[Learning Intelligence records: response latency improving — from 8 seconds (nervous) to 3 seconds (more comfortable). Engagement: WARMING_UP.]*

> **Sunita Ma'am:** "Ek aur baat — tumhari mummy ne bataya ki tum sometimes 'I know' bolti ho even when something is not fully clear. Ab main tumse clearly poochungi samajh aaya ya nahi — but mujhe chahiye ki tum sach bolna. Koi judgment nahi hai. Galat answer dene se main tumse pyar kam nahi karungi."

**Priya (typed, and for the first time, more than two words):** "Okay Ma'am. Actually usually teachers embarrass karte hain class mein isliye I say I know."
*(Usually teachers embarrass in class so that's why I say I know.)*

> **Sunita Ma'am:** "Main woh teacher nahi hoon. Yahan sirf hum dono hain. Koi class nahi, koi aur student nahi. Sirf tum."

*[Learning Intelligence: Engagement score 82/100. Student opened up — trust established. Record: STUDENT_TRUST_SIGNAL.]*

**End of intro session (20 minutes):**
> **Sunita Ma'am:** "Priya, mujhe lagta hai hum bahut achha kaam karenge saath mein. Wednesday se Maths shuru karenge — Chapter 1 se. Aur main tumse ek promise maangti hoon: agar kuch samajh na aaye, ek baar 'I don't understand' bol dena. Deal?"

**Priya:** "Deal Ma'am."

Evidence record: `STUDENT_PROFILE_ESTABLISHED` — shy_student confirmed, builds trust through direct speech, responds to one-on-one honesty ✓

---

## PART C — REGULAR SESSIONS

---

### Day 5, Wednesday 5:30 PM — Skill 2 + Skill 3: Discovery → Chapter 1 Polynomials

**[DISCOVERY SESSION — 15 minutes first]**

> **Sunita Ma'am:** "Priya, before we open the Maths book — ek question. 
> Imagine tum akele ek room mein ho. Tum apni height se double height ki shelf par kuch rakhna chahti ho. Kya use karogi?"
> *(You're alone in a room. You want to reach a shelf double your height. What would you use?)*

**Priya:** "Stool? Ya chair?"

> **Sunita Ma'am:** "Haan. Ab socho — agar tumhari height X hai, stool ki height Y hai — kitni total height?"

**Priya:** "X plus Y."

> **Sunita Ma'am (excited):** "Exactly! Tumne abhi algebra kar liya. X and Y — real life mein yahi hota hai — unknown cheezein jo milke kuch known result deti hain. Chapter 1 ka poora naam hai Polynomials — yeh sirf yahi hai. Heights, speeds, distances — real numbers jo hum jaante nahin, unhe represent karte hain."

*[Whiteboard — teacher draws: "Height of you = X" + "Height of stool = Y" + "Total = X + Y" — student watches it appear as teacher speaks.]*

> **Sunita Ma'am:** "Wednesday se aaj tak — this is what we're exploring. Ready?"

**ENGAGEMENT SCORE: 89/100** — Discovery Session working as designed.

---

**[CONCEPT TEACHING — 30 minutes]**

> **Sunita Ma'am:** "Polynomial ka matlab hota hai — 'many terms'. Poly = many, nomial = terms. Jab hum X² + 3X + 2 likhte hain — teen terms hain — yeh ek polynomial hai."

*[Whiteboard draws: X² + 3X + 2 with each term circled and labeled: "Term 1", "Term 2", "Term 3"]*

> **Sunita Ma'am:** "Priya, yeh X² + 3X + 2 mein kitne terms hain?"

**Priya:** "Teen. Three terms."

> **Sunita Ma'am:** "Perfect. Ab degree kya hoti hai — yeh sunna. Degree = highest power of X. Yahan X² hai — so degree = 2. Tum batao: 5X³ + 2X - 7 mein degree kya hai?"

**Priya (4 second pause):** "3?"

> **Sunita Ma'am:** "Bilkul sahi. 3 — because the highest power is X³. Whiteboard pe likho — 5X³ + 2X - 7 — aur circle karo highest power wala term."

*[Priya uses mouse to draw on her side of the whiteboard — she circles X³.]*

> **Sunita Ma'am:** "Perfect. See — tumne khud kiya. This is how we'll work — I explain once, you do the next one."

*[Learning Intelligence: Response latency = 2-4 seconds. Engagement = 91/100. Priya is actively participating — first mathematical confidence signal.]*

---

**[THE "I KNOW" MOMENT — Catching it honestly]**

> **Sunita Ma'am:** "Ab zeroes of a polynomial. Jab hum polynomial = 0 karte hain, jo value of X aati hai use zero kehte hain. Samajh aayi?"

**Priya:** "I know."

*[Learning Intelligence: response was immediate — 0.8 seconds. Suspicion signal: TOO_FAST_AGREEMENT. Flag: POSSIBLE_FALSE_CONFIRMATION]*

> **Sunita Ma'am (not challenging, just curious):** "Achha — toh mujhe ek example mein dikhao. X² - 5X + 6 = 0 mein zeroes kya honge?"

**Priya (12-second silence):** "..."

> **Sunita Ma'am (warm, no embarrassment):** "Ruko — main samajh gayi. 'I know' bol diya — but actually zero concept abhi settle nahi hua hai. That's totally okay — yeh concept tricky hai. Let me try again."

*[Attempt 1 — Different analogy:]*
> "Socho ek seesaw. Ek taraf X² - 5X + 6 hai — weight ki tarah. Jab X = 2 daalo, kya hota hai?
>  2² - 5(2) + 6 = 4 - 10 + 6 = 0. Seesaw balance ho gaya! Toh X = 2 ek zero hai."

**Priya:** "Ohhh — jab balance hota hai!"

> **Sunita Ma'am:** "Exactly. Ab tum karo: X = 3 daalo same polynomial mein."

**Priya (calculates on whiteboard — working visible):** "3² - 5(3) + 6 = 9 - 15 + 6 = 0!"

> **Sunita Ma'am:** "YES! Toh X = 3 bhi ek zero hai. Aur tumne khud nikala. Notice karo — tumne 'I know' bola tha — lekin tumhe actually pata nahi tha. That's not a problem. That's honest. Main is wajah se tumse directly poochti rehungi."

*[Learning Intelligence: FALSE_CONFIRMATION caught → attempt_1 successful → CONCEPT_UNDERSTOOD. Student Knowledge Graph updated: zeroes_of_polynomial = PARTIAL → confident after example.]*

Evidence: `CONCEPT_UNDERSTOOD_AFTER_REEXPLANATION` — tracks that this concept required reapproach ✓

---

### Day 6, Thursday — Skill 7: Homework Helper (8 PM)

**Priya (WhatsApp message):** "Ma'am, Q5 samajh nahi aaya homework mein"

> **Sunita Ma'am (WhatsApp voice, 40 seconds):**
> "Priya, pehle mujhe batao — Q5 mein tumne kya try kiya? Whiteboard pe likho jo tumne socha — app kholo, main dekhti hoon."

*[Priya opens whiteboard — writes: "X² + 7X + 12" with a question mark]*

> **Sunita Ma'am:** "Achha — toh polynomial hai. Question kya pooch raha hai?"

**Priya:** "Zeroes find karo."

> **Sunita Ma'am:** "Kaise nikalte hain zeroes — remember the seesaw? X kaunsi value pe = 0 hogi?"

**Priya (working, 45 seconds visible on whiteboard):** "X = -3 and X = -4?"

> **Sunita Ma'am:** "Verify karo — X = -3 daalo original mein."

**Priya:** "(-3)² + 7(-3) + 12 = 9 - 21 + 12 = 0. Sahi hai!"

> **Sunita Ma'am:** "Tumne khud nikala. Note karo — main tumhe answer kabhi seedha nahi dunga. But mujhe problem miss karna hai ki tum stuck kahan ho — that's my job."

**Constitutional:** Homework Helper academic integrity maintained. No answer given. ✓

---

### Day 8, Saturday 5:30 PM — Learning Intelligence Detecting Disengagement

Priya had a tough day at school (math test she thinks went badly). She's tired and distracted.

*[Session starts. Sunita Ma'am notices immediately.]*

**Response latency in first 5 minutes:** 8-12 seconds (vs usual 2-4)
**Response quality:** One-word answers only
**Engagement Score: 41/100 — LOW**

*[Trigger: STORY_PIVOT]*

> **Sunita Ma'am:** "Priya, ek minute ruko. Chapter baad mein — pehle ek baat sunao. Kya tum jaanti ho ki Emmy Noether koi thi? Unhe Nazi Germany ne university se nikaala was because she was a woman and Jewish. Unhone tab kya kiya? Ek drawing room mein students ko padhaya — secretly, informally. Aur unhone aisa mathematics discover kiya jisko aaj physics ki neenv kehte hain. Albert Einstein ne unhe 'the most significant creative mathematical genius' kaha tha."

*[Whiteboard draws: Emmy Noether's portrait sketch (simple line drawing) + one of her theorems]*

**Priya's response latency drops:** 10 seconds → 3 seconds
**Priya:** "She was thrown out? And still did that?"

> **Sunita Ma'am:** "Still did that. Aur jis chapter mein hum hain — Number Theory — yeh usi building block ka hissa hai jo Noether ne use kiya. Tum aaj wahi explore kar rahi ho jo usne explore kiya."

**Engagement Score: 78/100** — Story pivot worked. Session continues.

*At 40 minutes:*
**Engagement Score: 28/100** — Fatigue. Not disinterest — genuine tiredness.

*[Trigger: SESSION_END]*

> **Sunita Ma'am:** "Priya, aaj bahut achha kiya — especially Noether wala context samajhna. Hum 10 minute pehle bandh karte hain aaj. Fresh mind kal."

**Parent notification (WhatsApp to Meera):** "Today's session ended 10 minutes early — Priya seemed tired. We covered the first half of Number Theory. She connected well with a story about Emmy Noether — recommend asking her about it at dinner. She'll surprise you."

*[Meera later at dinner asks Priya about Emmy Noether. Priya talks for 5 minutes. Meera is surprised.]*

---

## PART D — PARENT PROGRESS REPORT

---

### Day 9, Sunday Evening — Skill 9: Parent Progress Report

**WhatsApp voice (Sunita Ma'am's voice, ~90 seconds):**

> "Meera ji, yeh raha Priya ka is hafte ka update.
>
> Is hafte humne Polynomials ka Chapter 1 khatam kiya — degree, zeroes, and factorisation. Priya on schedule hai exam ke liye.
>
> Jo achha hua: Priya ne zeroes nikaalte waqt khud verify kiya bina pooche — yeh ek bahut achha sign hai ki concept settle ho rahi hai.
>
> Ek area jo dekh rahi hoon: Priya 'I know' bolti hai jab actually concept fully settle nahi hua hota. Maine isko directly address kiya — usne bahut well respond kiya jab main ne bina embarrassment ke check kiya. Yeh aage improve hota rahega.
>
> Engagement observation: Saturday session mein Priya thodi tired thi — early close kiya. Best focus Monday-Wednesday hai. Agar possible ho, Saturday sessions thodi shift ho sakti hain.
>
> Ek kaam tumse: Aaj raat khane ke time Priya se Emmy Noether ke baare mein poochho — us par ek story share ki thi. Agar woh khud explain kar sake, toh concept pakka ho gayi hai."

**Portal (full detail):**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WEEK 1 — PRIYA'S PROGRESS REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sessions:     3 of 3 scheduled (1 ended 10 min early)
Time studied: 1 hr 50 min
Topics:       Maths — Ch.1 Polynomials (80% complete)

Strength:     Concept verification — Priya independently
              double-checks answers. Strong sign of mathematical
              thinking (not just formula application).

Watch for:    'I know' habit — teacher is actively managing.
              Priya responds well when checked with a question
              rather than "do you understand?"

Engagement:   Best: Mon + Wed (91/100, 89/100)
              Lowest: Sat (tired — 41/100 before story pivot)
              Teacher recommendation: consider Sat as makeup slot,
              not primary session.

Next week:    Complete Ch.1 → End of chapter quiz (Friday)
              Start Ch.2: Linear Equations

Exam readiness:  2 of 12 chapters covered | 10 weeks to mid-term
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Meera's response (WhatsApp):** "She talked about Emmy Noether for 5 minutes at dinner. First time she's ever talked about Maths at the table. I'm very impressed."

---

## PART E — GAPS SURFACED IN SIMULATION

| # | Gap | Severity | Resolution needed |
|---|---|---|---|
| **GAP-T001** | No trial session in spec | High | Add 1 free trial session (Skill 0 intro as trial) — data deleted in 7 days if parent doesn't convert |
| **GAP-T002** | "I know" detection not in Skill 3 spec | High | Add `FALSE_CONFIRMATION_DETECTION` explicitly to Skill 3 — fast agreement on new concept triggers a follow-up question |
| **GAP-T003** | Whiteboard interaction for student not fully specified | Medium | Spec says "student interacts via mouse" but doesn't specify what the student CAN draw vs. what's teacher-only. Add: student has own area, teacher area is view-only for student |
| **GAP-T004** | Post-session parent WhatsApp notification not in Skill 9 spec | Medium | Weekly report is specified; but real-time session notifications (session ended early, positive signal) are not. Add: lightweight post-session note to parent after each session (2-3 lines, not full report) |
| **GAP-T005** | Homework Helper channel not specified | Low | Spec says "student initiates" but doesn't specify the channel. Is it WhatsApp text, in-app, or only in the whiteboard session? For Class 9-10 students, WhatsApp at 8 PM for homework help is the most natural pattern. |
| **GAP-T006** | Story bank for teacher not specified | Medium | The Emmy Noether story was correct and context-appropriate. But "story-based teaching" needs a Tier 1 RAG specifically for: stories about scientists, mathematicians, historical figures by subject × standard × topic. Without this, teacher defaults to generic stories. |
| **GAP-T007** | Saturday performance dip — schedule advisory not automated | Low | Skill 9 noticed Saturday was low-engagement. The spec doesn't have a mechanism to proactively suggest schedule changes. Add to Skill 9: auto-suggest schedule adjustment if 3 consecutive sessions on same day are low-engagement. |

---

## Confidence Assessment

| Spec area | Simulation result | Grade |
|---|---|---|
| Parent onboarding conversation | Smooth 6-exchange flow — complete in 10 minutes | ✅ A |
| Teacher persona accuracy | "Won't accept 'I know'" correctly implemented | ✅ A |
| Skill 2 Discovery Session | Emmy Noether hook — student went from one-word answers to 5-minute dinner conversation | ✅ A |
| Skill 3 Teaching mode | Hindi-English mix correct; whiteboard used; adaptive reexplanation (seesaw analogy) worked | ✅ A |
| Skill 7 Homework Helper | Academic integrity maintained — guided not solved | ✅ A |
| Skill 5 Learning Intelligence | Saturday fatigue detected, story pivot worked, session ended early correctly | ✅ A |
| Skill 9 Parent Report | Barclays RM format worked — one ask (dinner question), actionable insight (Saturday schedule) | ✅ A |
| Trial session | **MISSING** — high-priority gap | ❌ GAP-T001 |
| FALSE_CONFIRMATION detection | Works in simulation but not explicitly specified in Skill 3 | ⚠️ Needs spec update |

**Overall:** The agent behaves like a genuinely excellent tutor in this simulation — warm, adaptive, honest, story-driven, and parent-informing. The core product experience is Grade A. The critical missing piece is the trial session (GAP-T001), which every parent will ask for.

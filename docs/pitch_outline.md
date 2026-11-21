# PrzetarGO — 5-minute pitch outline

HackNation 2026, Bydgoszcz. Challenge: Odwołania2JSON, Urząd Zamówień Publicznych. Pitch: Sunday 22 November 2026, 15:15 (Europe/Warsaw). Code freeze: 11:00 the same day.

Use this as a slide-by-slide script, not as on-screen prose. Keep slides short; say the notes. Replace every `[UPDATE: …]` after the last evaluation run. Target: about 3.5 minutes of talking and a 90-second live demo.

---

## Slide 1 — Title

**PrzetarGO: from a KIO case file to UZP’s JSON, reliably**

- Odwołania2JSON — Urząd Zamówień Publicznych
- Marco Gnudi and Wiktor
- Rules first, Polish open model only where it helps

**Speaker notes:**
Good afternoon. We are Marco and Wiktor, and our project is PrzetarGO. UZP asked for a working tool that reads the documents in a KIO appeal case and writes one JSON file per document, in their exact schema. That is what we built: a local app you can drop a batch of files into, which classifies each one, extracts the fields, and gives you clean JSON — including scans, and including files that should be rejected. I’ll show you how it works, what it scores, and then a short live demo.

---

## Slide 2 — The problem

**A case is a bundle, not a single form**

- Appeals, powers of attorney, transfer confirmations — plus paperwork that must be ignored
- Born-digital PDFs and image-only scans, many layouts
- Missing values must be `null`; a wrong document must be `{}`; the schema is fixed

**Speaker notes:**
A KIO case does not arrive as one tidy form. It is a bundle: the appeal itself, a power of attorney, a payment confirmation, and often other files that should not be classified at all. Some PDFs have a real text layer. Some are scans with no text at all. Layouts differ from case to case. UZP is clear about the output: keep every template key, use JSON `null` when a value is not reliable, and return an empty object when the file is not one of the three types. The hidden test set is real cases, and the score is field-level F1. A wrong value is more expensive than leaving a field empty, because it counts as two errors.

---

## Slide 3 — What we built

**A local app with a predictable pipeline**

- Drop a batch of files, see each result, download UZP-shaped JSON
- Read text if it is there; run Polish OCR only when it is not
- Classify first; extract with rules; optionally ask Bielik to fill the gaps

**Speaker notes:**
PrzetarGO is a small local web app. You drop in a batch of documents. For each file we first try the PDF text layer. If a page has almost no text, we run Tesseract in Polish. Then a rule-based classifier decides the type — or decides the file is irrelevant and we return empty JSON. For a known type, deterministic extractors pull the fields and check identifiers such as IBAN, NIP, REGON and PESEL. Only after that, if you switch on Bielik mode, the model is asked to fill fields that are still null, copying from the source text rather than inventing values. Everything is then normalised to UZP’s schema.

---

## Slide 4 — How the pipeline decides

**Deterministic where we can, a model where we must**

- Three modes: Regular, Bielik, and Bielik only
- Checksums repair or reject noisy numbers instead of guessing
- One shared path for the API, the UI and evaluation

**Speaker notes:**
There are three modes, and we are deliberate about them. Regular is rules only — free, instant, and already very strong on digital PDFs. Bielik mode still starts with rules, then asks the model only for the remaining gaps, and the UI shows where they agree. Bielik-only exists so we can measure the model on its own; it is not the path we would put in production. Identifiers are validated. If a number fails its checksum, we try a handful of common OCR confusions, and if it still fails we output null rather than a plausible-looking wrong value. Every mode goes through the same reader and the same normaliser, so what you see in the UI is what `evaluate.py` scores.

---

## Slide 5 — Results so far

**Strong on digital documents; scans are the work in progress**

| Split | Regular F1 | Bielik F1 |
|---|---:|---:|
| Text PDFs (180) | 0.983 | 0.979 |
| Scans (30) | 0.459 | 0.509 |
| Negatives (16) | 1.000 | 1.000 |
| Overall | 0.927 | 0.926 |

- Classifier: 196/196 on the text training set including decoys
- Scan figures are from 21 November, before a clean Polish OCR rerun — **to be updated**

**Speaker notes:**
[UPDATE: swap in the final table and speak those numbers only.] On the official born-digital training PDFs we are at about 0.98 F1, in both Regular and Bielik modes. All sixteen negative documents come back as empty JSON, so we do not invent a type when there isn’t one. The classifier has not missed a training file. Scans are the honest weak spot: these numbers, around 0.46 to 0.51, were measured before we reran OCR with Polish language data and before the checksum repair work landed, so we will update them before we present. We would rather show you a lower bound now than a number we cannot defend.

---

## Slide 6 — Easy to extend

**A new document type is a config entry, not a rewrite**

- Add keywords, the output template, and an LLM prompt
- Optionally add a small rule extractor and a couple of test fixtures
- The API, the UI and the scorer stay the same

**Speaker notes:**
Stage 2 also scores how easily the system can grow. We designed that in from the start. To add a new administrative document type you add one entry to the document-types config: the classifier keywords, the JSON template with every key defaulting to null, and a short prompt for Bielik. Restart the server and the new type can already be classified, filled, normalised and evaluated. If the layout is stable, you can add a small rule extractor later for higher precision, and Regular mode will pick those fields up without a model call. You do not change the API contract or the interface. That is the path we would use if UZP wanted this pipeline for other document families after the hackathon.

---

## Slide 7 — A small, open, Polish model

**Bielik 11B, used sparingly**

- Open-source 11B instruction model, built for Polish
- About $0.40 per million tokens; rules and a cache keep most runs cheap
- The app runs locally without a GPU; the model is called over an API

**Speaker notes:**
We did not put a large general model at the centre of the system. The only language model is Bielik 11B Instruct, an open Polish model. It is small, it reads this kind of language well, and it is called only after rules have done their work. A million tokens is on the order of forty cents, and repeated documents are served from cache. Regular mode costs nothing. The brief asked for open-source components and for an application that can run on-premise without a GPU, with the model reached by API. That is what we have. One caveat we will mention to the jury: our current inference route may go through hosting in Switzerland. The text is used for inference only, not for training, and we will follow the organisers’ guidance if they require an EU or Polish host for the official run.

---

## Slide 8 — Demo and what is next

**What you will see, and what we would do next**

- Live: a mixed batch — a text PDF, a scan, a decoy, and a rejected `.txt`
- Next: finish scan quality, complete DOCX support, add types from config
- We would like this to become a UZP pilot for other administrative PDFs

**Speaker notes:**
I will run a ninety-second demo next: a mixed batch, Regular versus Bielik, and the JSON you would actually submit. After the freeze, the remaining work is clear — finish the scan quality improvements, complete Word document support, and keep adding types through configuration rather than new architecture. We think this can be more than a hackathon prototype. UZP said strong solutions could become the basis for a pilot. We would be glad to talk about taking the same pipeline to other document types. Thank you — we are happy to take questions.

---

## 90-second live demo script

Prepare before you go on stage: UI already open at `http://127.0.0.1:8080`, API healthy, Tesseract with Polish data working, one folder containing exactly four files — a born-digital PDF of a known type, one file from `dane/skany`, one file from `dane/negatywne`, and a `.txt` file. Have Regular mode selected first, with “normalise JSON” on. Do not start a long uncached Bielik run live unless you have already warmed the cache for those files.

1. **The screen (about 10 seconds).** “This is the PrzetarGO UI. I am going to drop in four files at once: a normal PDF, a scan, a document that should be ignored, and a text file that is not supported.”
2. **Upload the batch (15 seconds).** Drag the folder onto the drop zone. Point to the `.txt` being rejected with a clear error, and to the other three continuing. “Unsupported files are skipped; the rest of the batch keeps going.”
3. **Regular results (25 seconds).** When the three documents finish, open the text PDF: show the type, the extracted fields, the `text` source badge, and the timer. Open the decoy: show `{}`. Open the scan: show the `ocr` badge and that fields were still produced. “Regular mode used no language model.”
4. **Toggle Bielik (25 seconds).** Switch the same batch to Bielik mode and rerun (cached if needed). On a document where the model filled a gap, point at a “Rules ✓ Bielik” agreement badge, and at any field only one side found. “Rules still run first. The model is only asked to fill nulls, and we can see where they agree.”
5. **JSON out (15 seconds).** Open Show JSON, Copy, then Download. “This is the UZP schema: every key is present, missing values are null, and the rejected file is an empty object. That is the file we would hand over.”

If something fails live, switch to a prepared screenshot or a saved `reports/` output and say so in one sentence. Do not debug on stage.

---

## Likely judge questions

**1. Why rules and a language model, rather than only one of them?**
Rules are fast, free, and exact on stable labels and checksummed identifiers. They also give us a reliable classifier, which is how we return `{}` for irrelevant files. The model is better at wording that the regex did not anticipate. We run rules first and let Bielik fill remaining nulls, so we keep control over numbers and still recover fields we would otherwise miss. Bielik-only exists so we can measure the difference, not as the default.

**2. Why this model size? Why not a larger or a vision model?**
The brief rewards a small, open model and requires open-source components. Bielik 11B is a Polish instruction model, which matches the documents, and 11 billion parameters keeps us in honest “small model” territory. A large closed model would be the wrong fit for the rules and for the score. We did not put a vision model on every page. If scan F1 is still too low after Polish OCR and checksum repair, the fallback we would consider is a small open vision model, used only on fields that fail validation — and we would check that with the organisers first.

**3. What does it cost to run?**
Regular mode costs nothing beyond the machine it runs on. Bielik is on the order of forty cents per million tokens, and we only send the fields that rules left empty. A cache keyed on the prompt and the document text means a repeated file is free. For a typical training document the model is a small part of the work, not a full-document rewrite.

**4. Where does the document text go, and is that acceptable?**
The application runs locally. Regular mode never leaves the machine. In Bielik modes, the extracted text is sent as a prompt to the configured API endpoint and is not used to train the model. Our current route may use Hugging Face / Public AI hosting in Switzerland. We will follow the organisers if they require an EU or Polish endpoint for the official evaluation, and the client is already configured by environment variables, so the host can be changed without rewriting the pipeline.

**5. How do you handle scans, and why is that F1 lower?**
Scans in the official set are image-only: there is no text layer, so we render the page and run Tesseract in Polish. We then clean typical OCR confusions and validate identifiers. The published scan scores were taken before a clean Polish OCR rerun and before those repairs, so they understate where we expect to be. Even then, scans will likely remain harder than digital PDFs — different DPI, stamps, and skew — which is why we report them as a separate split instead of hiding them in the overall number.

**6. What does it actually take to add a new document type?**
One entry in the document-types config: classifier keywords, the output template, and an LLM prompt. Restart, and the existing pipeline can classify, extract with Bielik, normalise and score the new type. If you want Regular mode to be strong as well, add a small rule extractor and a few fixtures. You should not need to touch the API or the UI. That is the extensibility we are asking to be scored on, and it is how we would add the next UZP document family.

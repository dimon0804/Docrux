# Paragraf

A digital secretary for a university dean's office. A student uploads a photo of a certificate or an application and asks a question. The service reads the picture, fills in a card of fields, checks the required data and answers with a reference to the exact clause of the regulations.

Built for the "Online Dean's Office" case by Center-invest Bank. [Русская версия](README.md)

![Result: the check, answers with clause references and field highlighting](docs/screenshots/result-light.png)

| Home page | Reading a document | Dark theme |
| --- | --- | --- |
| ![Home page](docs/screenshots/home-light.png) | ![Reading a document](docs/screenshots/reading.png) | ![Dark theme](docs/screenshots/result-dark.png) |

## Features

**Required level**

- Accepts a photo or a scan in JPG, PNG or PDF and a question in Russian.
- Recognizes text with Tesseract.
- Fills in the card for three document types. An empty field gets the value "не найдено" (not found).
- Checks completeness against the regulations and lists what is missing.
- Names the source in every answer: a clause of the regulations or a document field.
- Says so plainly when neither the document nor the regulations contain the answer.

**Advanced level**

- Detects the document type on its own.
- Handles poor pictures: tilt up to 30°, shadow, glare, low resolution, a sheet photographed on a desk.
- A new document type is one YAML file, with no code changes.
- Shows where each field was found on the picture.

**Beyond the brief**

- Reads certificates and applications written as running text, not only forms. Names are put into the nominative case.
- Does not reject documents of other types. For a protocol or an order it shows the title, the text and the label-value lines it found, and explains why such a document cannot be checked against the regulations.
- Reads PDF files up to 10 pages.
- Tells what the uploaded document is and answers questions about the regulations by quoting the right clause.

## Quick start

Docker is the only requirement.

```sh
git clone https://github.com/dimon0804/PARAGRAF.git paragraf
cd paragraf
docker compose up --build
```

Open <http://localhost:8080>. The home page offers three sample documents, one per type.

## Running in Google Colab

No Docker at hand? Open the notebook: it installs the service on a free Colab machine, checks the open set and builds `results.json` for any set in the same format.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dimon0804/PARAGRAF/blob/main/notebooks/paragraf_colab.ipynb)

## Producing results.json

```sh
docker compose build api
mkdir -p out
docker run --rm -v "$PWD/data/open:/data:ro" -v "$PWD/out:/out" paragraf-api \
  paragraf batch /data/documents.json --out /out/results.json

python data/open/evaluate.py \
  --reference data/open/reference_results.json \
  --predictions out/results.json
```

Point the command at the closed set folder to process it. Document types are taken from the manifest. The output follows `results.schema.json`, which a test verifies. A damaged file does not stop the run: it gets an empty card and a warning. Only the answer kinds defined by the format go into `results.json`; document summaries and quotes from the regulations work in the interface only.

## Quality

All numbers come from recognizing images. The PDF text layer is not used.

| Set | Documents | Fields | Check | Questions |
| --- | ---: | ---: | ---: | ---: |
| Open set from the organizers | 30 | 1.000 | 1.000 | 1.000 |
| Our own documents in the same layout | 90 | 1.000 | 1.000 | 1.000 |

Our own documents are produced by `tools/synth.py` with different names, universities, group codes and numbers. This shows that the service reads the document instead of remembering the open set.

Free-form documents come from `tools/freeform.py`: 42 certificates and applications written as running text, with no type hint.

| Set | Type detected | Fields |
| --- | ---: | ---: |
| Free-form documents | 42 of 42 | 0.990 |

Robustness was measured on the same 90 documents damaged by `tools/degrade.py`:

| What was done to the picture | Fields | Check | Questions |
| --- | ---: | ---: | ---: |
| Tilt up to 30° | 1.000 | 1.000 | 1.000 |
| Shadow over half of the sheet | 1.000 | 1.000 | 1.000 |
| Lamp glare | 1.000 | 1.000 | 1.000 |
| Low resolution, about 600 pixels wide | 1.000 | 1.000 | 1.000 |
| Heavy JPEG compression | 1.000 | 1.000 | 1.000 |
| Blur and noise | 0.998 | 0.978 | 1.000 |
| Sheet photographed on a desk: perspective, tilt, shadow, compression | 1.000 | 1.000 | 1.000 |

## How it works

1. **Intake.** The format is detected from the file content, not from its extension. PDF pages become images.
2. **Preparation.** The service finds the sheet on the desk and fixes perspective, estimates the tilt, evens out the light and enlarges small photos. When the sheet contour is doubtful, the picture is left uncropped.
3. **Recognition.** Tesseract 5 with the accurate Russian model returns words and their coordinates.
4. **Card.** Lines shaped like "Label: value" are matched to fields by fuzzy label comparison. Dates become `YYYY-MM-DD`; look-alike letters and digits in codes are repaired.
5. **Signature and seal.** Only the presence of a drawing is checked. The words "Подпись" and "М.П." do not count: recognized text is subtracted before the analysis.
6. **Check.** The card is compared with the required fields of the type.
7. **Answer.** A question is one of: completeness, a field value, who makes the final decision. Anything else is treated as unanswerable. No language model writes the answer, so the service cannot invent a fact.

## Adding a document type

Put a file into `config/doc_types`:

```yaml
id: library_card
title: Читательский билет
fields:
  - key: reader_name
    label: ФИО читателя
    type: person
    rule: "1.1"
  - key: card_number
    label: Номер билета
    type: code
    rule: "1.1"
```

After a restart the type appears in the interface, in type detection and in answers. The regulations live in `config/rules.md`.

## Questions in the student's own words

The regulations say "the maximum length of the leave is not set", while a student asks "how long can I be away?". Short phrases from such questions are tied to clause numbers in `config/rules_hints.yaml`. The answer is always a verbatim quote of the clause.

We tried a small local language model for these questions (Vikhr-Qwen 1.5B through llama.cpp) and dropped it. It attached a real quote and then wrote something false on top of it, and it answered three of eighteen off-topic questions instead of refusing. The phrase hints reach the right clause on the same questions and never break a refusal.

## Handwriting

Tesseract reads printed text. For fields filled in by hand an open TrOCR model fine-tuned on Russian handwriting can be attached:

```sh
python tools/fetch_models.py handwriting
HANDWRITING_MODEL=/models/trocr-ru API_MEMORY=6g docker compose up --build
```

The model takes about 1.5 GB per worker process, so the service needs more memory than the default. In our run the container with the model used 4.2 GB.

In PowerShell set the variables first: `$env:HANDWRITING_MODEL="/models/trocr-ru"; $env:API_MEMORY="6g"; docker compose up --build`. In Git Bash put `MSYS_NO_PATHCONV=1` before the command, otherwise the shell rewrites `/models` into a Windows path.

Neither of the two versions we tested reads names reliably, so the model's reading is not treated as a fact. A value enters the card only when the printed OCR and the handwriting model independently read the same thing. Otherwise the field stays empty with a "filled in by hand" note and the model's reading is shown as a hint. On 30 documents filled in with handwriting fonts this cut wrong values in the card from 37 to 8. Reading accuracy did not improve.

## Tools and models

No external OCR or language model APIs are used. Everything runs on the CPU of an ordinary laptop.

The word loader comes from the open [Uiverse.io](https://uiverse.io) collection (by kennyotsu, MIT) and was adapted to the service. Interface colors are built on the brand green of Center-invest Bank.

| Purpose | Tool |
| --- | --- |
| Text recognition | Tesseract 5.5, `rus` model from `tessdata_best` |
| Image processing | OpenCV, Pillow |
| PDF reading | PyMuPDF |
| Label matching | RapidFuzz |
| Word stems in questions | Snowball (Russian stemmer) |
| Name cases | pymorphy3 |
| Handwriting (optional) | TrOCR `trocr-base-handwritten-ru` in ONNX, ONNX Runtime |
| HTTP API | FastAPI, Uvicorn, Pydantic |
| Interface | React, TypeScript, Vite, Tailwind CSS, Base UI, Motion, Sonner, Lucide |
| Gateway | Caddy |
| Code checks | pytest, Ruff, Vitest, ESLint |

## Security and privacy

- A file is processed in memory and never stored. There is no database and there are no accounts.
- Only JPG, PNG and PDF up to 15 MB are accepted, with a limit on image size in pixels.
- Requests per address are rate limited.
- Containers run without root, with a read-only file system and no extra privileges. The API is not exposed; requests go through Caddy.
- A Content-Security-Policy and the other security headers are set. No third-party scripts, fonts or trackers are loaded.
- Logs hold the request time, the document type and the check result. Document contents are never logged.

## Development

```sh
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn paragraf.api.app:app --reload

cd frontend
npm install
npm run dev
```

Local recognition needs Tesseract with the Russian language. Tests read the PDF text layer of the open set, so they pass without it.

## Limitations

- Handwriting is not read reliably. Open models misread letters and the service must not invent, so a handwritten field stays empty unless its reading is confirmed.
- Phrase patterns for free-form documents cover common wordings, not all of them. They are extended in the config with no code changes.
- Up to 10 pages of a PDF are read. Pages are joined into one picture and fields are searched on all of them.
- The presence of a signature and a seal is checked, not their authenticity.
- The check is preliminary. The final decision belongs to a dean's office employee, clause 1.3 of the regulations.

## License

MIT. The data in `data/open` belongs to the hackathon organizers; all details in it are fictional.

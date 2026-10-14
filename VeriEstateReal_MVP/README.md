# VeriEstateReal MVP — Setup and Demo Guide

This is a local educational prototype aligned with the VeriEstateReal concept note and internship presentation. It includes Flask, SQLite, document text extraction, rule-based mismatch checks, a scikit-learn duplicate-candidate model, synthetic model evaluation, and a manual-review queue.

## Important limits

- No government portal is connected.
- It does not verify legal ownership/title and cannot certify a property as fraud-free.
- The ML model is trained/evaluated using generated synthetic listing pairs only. Its scores are **not real-world performance estimates**.
- Do not expose this development app to the public or upload private property documents. The starter app has no user login/security review.

## Requirements

Windows 10/11 and Python 3.10–3.12 recommended. Internet is needed for the initial Python package install. Optional image OCR requires separately installed Tesseract OCR.

## Quick start (Windows PowerShell)

1. Unzip this folder somewhere easy to find, such as your Desktop. Open the extracted `VeriEstateReal_MVP` folder in VS Code. In VS Code choose **Terminal → New Terminal**.
2. Check Python:

```powershell
py --version
```

3. Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If activation is blocked, use the environment's Python executable directly (commands below).

4. Install packages:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If you skipped activation, run:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

5. Train the ML demonstration and save its synthetic-data evaluation metrics:

```powershell
python train_model.py
```

6. Load fictional demo listings:

```powershell
python seed_demo.py
```

This inserts five sample listings only if the database is empty. They are made up, not actual property records.

7. Start the web app:

```powershell
python app.py
```

8. Open **http://127.0.0.1:5000** in your browser. Keep the terminal open while using it. Press `Ctrl+C` in the terminal to stop the app.

## Demonstration flow

1. Dashboard: show system status, listing/document/comparison counts, and synthetic model metrics.
2. Listings: open the fictional sample listings.
3. Document upload: open a listing and upload `data/SAMPLE_DOCUMENT.txt` to demonstrate text extraction and suggested field parsing.
4. Compare: choose Listing A and its similar variant, then run the ML comparison.
5. Explain results: describe features such as address similarity, locality/city/type match, area difference, identifiers and description similarity. Explain that the probability is only a synthetic demo signal.
6. Review queue: add a reviewer note and mark the item reviewed.
7. Export listing metadata to CSV if useful.

## Technical explanation for an evaluator

- **ML task:** classify listing pairs as potential duplicates or non-duplicates, not determine fraud.
- **Features:** address similarity, locality/city/property type matches, relative area difference, ID presence/match, and description similarity.
- **Baseline:** a simple address/locality/property-type heuristic is evaluated alongside the classifier; baseline and model metrics are saved by the training script. The app separately shows explicit mismatch rules.
- **Model:** RandomForestClassifier from scikit-learn trained by `train_model.py` on synthetically generated pairs.
- **Evaluation:** precision, recall, F1-score, accuracy and confusion matrix, on a held-out synthetic set.
- **Limit:** synthetic data demonstrates the pipeline only. Real use requires authorized representative listings, documented human labels, leakage-aware splitting, recalibration, and fresh evaluation.
- **OCR:** text PDFs/TXT work directly. Image OCR requires Tesseract; scanned PDFs may need a separate OCR step.

## Troubleshooting

- `py` or `python` not found: install Python from python.org and select “Add Python to PATH”, then reopen VS Code.
- `ModuleNotFoundError`: activate `.venv`, then reinstall with `python -m pip install -r requirements.txt`.
- “ML model not trained”: run `python train_model.py`, then stop/restart `python app.py`.
- No listings: run `python seed_demo.py` (only seeds an empty database).
- PDF text not found: use a text-based PDF or the provided TXT sample for the first demo; scanned PDF OCR is not automatic.
- Image OCR fails: install Tesseract OCR separately and ensure `tesseract.exe` is on PATH.
- Reset the demo: stop app, back up needed data, delete `instance/veriestate.db`, then rerun `python seed_demo.py`.

## Suggested project demonstration sequence

Explain the problem → show the architecture → show the dataset-generation/training script → show metrics with the synthetic-data warning → run the Flask app → compare two fictional listings → inspect mismatch notes → show human review. Do not claim public-record verification or model performance on real listings.


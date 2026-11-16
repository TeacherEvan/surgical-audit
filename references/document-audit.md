# Document Audit Reference — Document & Resume Harmonization

**Applies to:** Multi-file document packs (CV/resume bundles, portfolio HTML, exported PDFs, signed reference letters, credential dossiers)
**Purpose:** Verify cross-file consistency across exported formats, timelines, legal-vs-trading names, and ATS extractability without inventing or mutating user data.

---

## Critical Verification Checklist

### Email & Contact Consistency

- **Rule:** Maintain a single canonical contact email, phone format, and portfolio URL across all files in the pack.
- **Verification:**

  ```bash
  grep -rnE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' \
    --include="*.html" --include="*.md" --include="*.txt" .
  ```

- **Pitfall:** An earlier alias or typo (`<old-alias>@example.com`) persists in a footer or metadata tag after migrating to `<user>@example.com`. Run text extraction on PDFs too so header/footer mismatches do not slip into submissions.

### Timeline Reconciliation

- **Rule:** No unexplained overlapping full-time roles across the document pack; all gap explanations and dates match supporting letters.
- **Verification pattern:**

  ```bash
  grep -rnE '\(?20[0-9]{2}\s*[-–]\s*(20[0-9]{2}|Present)\)?' --include="*.html" --include="*.md" .
  ```

- **Common issue:** A transitional or part-time role extends past the start date of a subsequent full-time appointment in another file version. Reconcile exact start/end months across every variant (`*-Visual.html`, `*-ATS.pdf`, cover summary).

### Permit / Registry vs. Employer Name Alignment

- **Rule:** Legal entity names and trading/brand names must map unambiguously across filings and resumes.
- **Pitfall:** Official registration or permit paperwork lists `"Employer Legal Name Ltd."` while the resume header uses `"Employer Trading Name"`.
- **Decision:** Keep the primary employer name matching signed reference documentation, and add a brief parenthetical or caption clarifying the legal-entity relationship when submitting both documents together.

### Reference Letter Cross-Check

- **Rule:** Every role title and date range claimed in the resume matches signed referee letters verbatim.
- **Verification:** Extract text from each letter (`pdftotext <letter>.pdf -`) and verify exact year/month spans against HTML and PDF resume editions (for example, referee letter `"2018–2022"` must match resume entry `"2018–2022"`).

### ATS-Compatibility Check

- **Rule:** Exported PDFs must expose a clean, selectable UTF-8 text layer in logical reading order.
- **Verification:**

  ```bash
  pdftotext output.pdf - | head -n 40
  pdfinfo output.pdf
  ```

- **Pitfall:** Flattened/rasterized scans or multi-column CSS grids that serialize text out of order cause Applicant Tracking Systems (ATS) to drop dates or merge unrelated bullet lists.

---

## Expected Document Pack Structure

```text
DOCUMENT_PACK_ROOT/
├── index.html                        # Primary web portfolio entry
├── <Candidate_Name>_Portfolio.html   # Detailed formatted view (print/PDF source)
├── <Candidate_Name>_Resume_YYYY.pdf  # ATS-friendly exported submission
├── credentials/
│   ├── degree_certificate.pdf        # Verified graduation date & title
│   ├── professional_cert.pdf         # Credential ID & issue date
│   └── registration_records/         # Legal-name alignment proof
└── references/
    ├── referee_1_signed.pdf          # Signed date span matching resume
    └── employer_commendation.pdf
```

---

## Automated CLI Cross-Check Recipe

Run a zero-mutation cross-file check directly in the document directory:

```bash
# 1. Extract unique email addresses across HTML/Markdown sources and PDFs
{
  grep -rhoE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' --include="*.html" --include="*.md" .
  for pdf in ./*.pdf credentials/*.pdf references/*.pdf; do
    [ -f "$pdf" ] && pdftotext "$pdf" - | grep -oE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
  done
} | sort -u

# 2. Verify every exported PDF has a non-empty extractable text layer
for pdf in ./*.pdf; do
  [ -f "$pdf" ] || continue
  chars=$(pdftotext "$pdf" - | wc -c)
  printf '%s: %s text chars\n' "$pdf" "$chars"
done
```

Expect exactly one canonical contact email in step 1 and non-zero searchable text length in step 2.

---

## Pitfall: Contact & Domain Migration

When updating contact details across a document pack:

1. Update the canonical source (`index.html` / template HTML) first.
2. Regenerate PDF exports directly from the updated HTML source.
3. Verify the retired address (`<old-alias>@example.com`) returns `0` matches across HTML, Markdown, JSON-LD metadata, and extracted PDF text.
4. Update any site configuration or metadata manifest that repeats contact links.
5. Never ship two conflicting contact addresses inside the same submission pack.

---

## Authenticity & Consistency Markers

| Element | Authentic State | Non-Authentic Warning |
| :--- | :--- | :--- |
| Contact Email | Single canonical address (`<user>@example.com`) | Multiple addresses, stale aliases, typos |
| Employment Dates | Zero unexplained overlaps; matches signed letters | Extended beyond supporting evidence |
| Outcomes & Metrics | Quantifiable, bounded impact statements | Unbounded vague claims without scope |
| Certifications | Issue dates, credential IDs, and issuing bodies present | Missing dates or altered credential names |
| References | Verified referee names matching signed letters | Unverified contacts or mismatched date spans |

---

## Export Provenance Cross-Check

When multiple export passes generate HTML/PDF artefacts in a workspace:

1. Record the exact source commit SHA, build tool/template version, and generator configuration used for each export batch.
2. Verify all artefacts in one submission bundle were generated from the **same** source revision rather than mixing yesterday's PDF with today's HTML.
3. Compare generated text (`pdftotext` vs HTML body copy) after any regeneration rather than relying solely on filesystem timestamps.

# CLAIM_GRAPH_SPEC.md — magicpin "Build Vera Better" Challenge

**Claim Graph Engine & Grounding Verification Specification**
*Author: Lead AI & Systems Engineer*

---

## 1. Overview & Architectural Intent

In `judge_simulator.py`, the AI Judge penalizes submissions with **-2 points for data fabrication** whenever a message contains claims not present in the context.

Naive regex exact matching fails because LLMs naturally reformat numbers (e.g., `2580` -> `2.58k` views; `0.021` -> `2.1% CTR`; `299` -> `₹299`).

The **Claim Graph Engine** builds an explicit graph of **Approved Facts** and their **Permitted Transformations**, ensuring 100% grounding without penalizing legitimate linguistic formatting.

---

## 2. Claim Graph Node Architecture

Each node in the Claim Graph represents an approved factual claim extracted from the context:

```python
from dataclasses import dataclass, field
from typing import List, Any, Set

@dataclass
class ClaimNode:
    claim_id: str                      # Unique ID (e.g. "claim_views_meera")
    source_context: str                # Scope & path (e.g. "merchant.performance.views")
    context_version: int               # Version provenance (e.g. 2)
    claim_type: str                    # "count" | "percentage" | "currency" | "date" | "citation" | "duration"
    raw_value: Any                     # Raw underlying value (e.g. 2410, 0.021, "JIDA Oct 2026, p.14")
    permitted_transformations: Set[str] # Set of valid string representations
```

---

## 3. Permitted Transformation Rules Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PERMITTED TRANSFORMATION MATRIX                         │
├───────────────┬─────────────────┬──────────────────────┬────────────────────┤
│ Claim Type    │ Raw Value       │ Permitted Realizations│ Invalid (Penalty)  │
├───────────────┼─────────────────┼──────────────────────┼────────────────────┤
│ Count         │ 2410            │ "2410", "2,410",     │ "3000", "2500"     │
│               │                 │ "2.4k", "~2.4k"      │ (Hallucinated)     │
├───────────────┼─────────────────┼──────────────────────┼────────────────────┤
│ Percentage    │ 0.021           │ "0.021", "2.1%",     │ "21%", "5%"        │
│               │                 │ "2.1 percent"        │ (Math Error)       │
├───────────────┼─────────────────┼──────────────────────┼────────────────────┤
│ Currency      │ 299             │ "299", "₹299",       │ "₹199", "₹499"     │
│               │                 │ "Rs 299", "Rs. 299"  │ (Wrong Catalog)    │
├───────────────┼─────────────────┼──────────────────────┼────────────────────┤
│ Date          │ "2026-11-05"    │ "5 Nov", "Nov 5",    │ "12 Nov", "10 Dec" │
│               │                 │ "Wednesday 5 Nov"    │ (Wrong Slot)       │
├───────────────┼─────────────────┼──────────────────────┼────────────────────┤
│ Citation      │ "JIDA Oct 2026, │ "JIDA Oct 2026 p.14",│ "PubMed 2025",     │
│               │  p.14"          │ "JIDA (Oct 2026)"    │ "DCI Circular 2024"│
└───────────────┴─────────────────┴──────────────────────┴────────────────────┘
```

---

## 4. Verification & Validation Engine Algorithm

When the LLM Realizer outputs a candidate message body, the `ClaimGraphValidator` executes:

```
Candidate Message Body
         │
         ▼
1. Extract all numeric values, prices, percentages, dates, and citations via Regex:
   - Currency: r'(?:₹|Rs\.?\s*)(\d+(?:,\d+)*(?:\.\d+)?)'
   - Percentages: r'(\d+(?:\.\d+)?)\s*%'
   - Numbers: r'\b\d+(?:,\d+)*(?:\.\d+)?[kM]?\b'
   - Citations: r'\b(JIDA|DCI|IDA|PubMed|Practo)\b.*?'
         │
         ▼
2. For each extracted token T:
   - Check if T matches any raw_value or permitted_transformations in the ClaimGraph.
         │
         ▼
3. Is T grounded in the ClaimGraph?
   ├─► YES : Token approved.
   └─► NO  : GROUNDING VIOLATION DETECTED!
         │
         ▼
4. Grounding Violation Recovery:
   - If minor: Replace ungrounded token T with approved raw_value.
   - If major: Re-prompt LLM Realizer with explicit Grounding Error feedback,
     or fallback to Mode A Deterministic Template.
```

---

## 5. Explicit Challenge Citations

- **`judge_simulator.py` §5.1 (LLM Scorer)**:
  *"PENALTIES: Fabricating data not in context: -2. Score each dimension 0-10 with clear reasoning. Be STRICT."*
- **`challenge-brief.md` §5 (Constraints)**:
  *"8. Don't fabricate — if data isn't in the contexts, don't invent it. No fake offers, no fake research citations, no fake competitor names."*

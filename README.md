# ClaimRecon AI
> Bounded Agentic Claim-Package Validation & Supported-Amount Analysis  
> Hackathon MVP · LangGraph + Gemini + Streamlit

---

## Quick Start

### 1. Activate the virtual environment
```bash
cd claim_recon_ai
source .venv/bin/activate
```

### 2. Add your API key
Edit `.env` and fill in your key:
```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
GOOGLE_API_KEY=your-actual-key-here
```
> To use OpenAI: set `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o`, `OPENAI_API_KEY=...`  
> To use Anthropic: set `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-3-5-haiku-20241022`, `ANTHROPIC_API_KEY=...`

### 3. Run the CLI
```bash
# Complete package (all 3 findings, $760K supported)
python main.py data/complete_claim_package_clm_2026_0042

# Incomplete package (2 findings, partial result)
python main.py data/incomplete_claim_package_clm_2026_0042
```

### 4. Launch the Streamlit dashboard
```bash
streamlit run src/ui/dashboard.py
```
Then open http://localhost:8501 in your browser.

---

## Expected Results

### Complete Package
```
Claimed Amount:    $824,000
Supported Amount:  $760,000
Unsupported Amount: $64,000

Findings:
  FND-001  INV-5521  DUPLICATE_INVOICE_V1         $38,000
  FND-002  INV-9102  DELIVERY_AFTER_LOSS_V1        $24,000
  FND-003  INV-7742  INVOICE_AMOUNT_MISMATCH_V1     $2,000

✅ 760,000 + 64,000 = 824,000  (INVARIANT PASSES)
```

### Incomplete Package
```
Claimed Amount:             $824,000
Identified Unsupported:      $40,000
Supported Amount:            N/A (DELIVERY_AFTER_LOSS_V1 blocked)

Checks: 2 completed, 1 blocked, 0 failed
```

---

## Architecture

```
[load_claim_package] → [classify_documents] → [validate_classification]
       → [check_completeness] → [supervisor_plan] → [validate_plan]
       → [execute_checks] → [evaluate_completion]
              ├── CONTINUE → [supervisor_plan]  (loop)
              ├── COMPLETE → [calculate_supported_amount] → [generate_summary]
              ├── PARTIAL  → [calculate_partial_result]   → [generate_summary]
              └── REVIEW   → [generate_summary]
```

**LLM nodes (3):** `classify_documents`, `supervisor_plan`, `generate_summary`  
**Python nodes (7+):** everything else — all financial math is deterministic

## Project Structure
```
src/
├── state.py          # ClaimState TypedDict
├── config.py         # Checklist + Tool catalog (business rules)
├── llm_factory.py    # Provider-agnostic LLM factory
├── loaders.py        # JSON/Excel file readers
├── graph.py          # LangGraph pipeline
├── nodes/            # 10 graph nodes
├── tools/            # 3 integrity check implementations
└── ui/               # Streamlit dashboard
```


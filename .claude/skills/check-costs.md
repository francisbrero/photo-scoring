# Check Costs

Estimate or check API costs for photo scoring.

## Usage
```
/check-costs [photo-count]
```

## Instructions

When the user invokes this skill:

1. **Calculate estimated costs**

   Current cost per image: ~$0.005 (7 API calls)

   | Photos | Estimated Cost |
   |--------|----------------|
   | 10 | $0.05 |
   | 100 | $0.50 |
   | 500 | $2.50 |
   | 1000 | $5.00 |

2. **If user wants actual usage**
   - Direct them to OpenRouter dashboard: https://openrouter.ai/activity
   - Note: Claude Code cannot access their API dashboard directly

3. **Cost breakdown per image**
   ```
   Feature extraction (Pixtral 12B):     ~$0.0003
   Aesthetic scoring (Qwen + Gemini):    ~$0.0010
   Technical scoring (Qwen + Gemini):    ~$0.0010
   Metadata (Pixtral 12B):               ~$0.0003
   Critique (Gemini 3 Flash):            ~$0.0020
   ─────────────────────────────────────────────
   Total per image:                      ~$0.0046
   ```

## Example
```
/check-costs 500
```
Output: "Scoring 500 photos will cost approximately $2.50"

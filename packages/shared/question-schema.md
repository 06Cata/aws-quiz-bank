# Question JSON Schema

Supabase `questions` table keeps bilingual content in JSONB.

Local question files use `question_no` as the integer question identifier. Files are named by an inclusive, contiguous range and contain at most 15 questions, such as `Q1-Q10.json`, `Q11-Q25.json`, and `Q26-Q40.json`.

## question_text

```json
{
  "zh": "繁體中文題目",
  "en": "English question"
}
```


## options

```json
{
  "A": {
    "zh": "繁體中文選項 A",
    "en": "English option A"
  },
  "B": {
    "zh": "繁體中文選項 B",
    "en": "English option B"
  }
}
```

## option_explanations

```json
{
  "A": {
    "zh": "繁體中文解析",
    "en": "English explanation"
  }
}
```

## display rule

Frontend renders Chinese first, then English.

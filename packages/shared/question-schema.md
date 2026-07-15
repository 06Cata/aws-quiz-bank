# Question JSON Schema

Supabase `questions` table keeps bilingual content in JSONB.

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

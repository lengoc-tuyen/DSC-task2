# Canonical fine-tuning schema

Use this semantic hierarchy and key order. Omit a key only when its value would be null, an empty string, or an empty array. Never use omission to hide unparsed source text.

```json
{
  "document_id": 21,
  "document": {
    "type": "QUYẾT ĐỊNH",
    "number": "36/2012/QĐ-TTg",
    "title": "...",
    "issued_by": "...",
    "issued_place": "Hà Nội",
    "issued_at": "06/09/2012",
    "source": "https://..."
  },
  "legal_bases": ["Căn cứ ..."],
  "proposals": ["Theo đề nghị ..."],
  "enactment": "...",
  "parts": [
    {
      "type": "decision|regulation|appendix|form|list|main|other",
      "number": "I",
      "title": "...",
      "reference": "Ban hành kèm theo ...",
      "text": "Substantive text belonging directly to this part",
      "chapters": [
        {
          "number": "I",
          "title": "...",
          "text": "Direct chapter text",
          "sections": [],
          "articles": []
        }
      ],
      "sections": [
        {
          "number": "1",
          "title": "...",
          "text": "Direct section text",
          "subsections": [],
          "articles": []
        }
      ],
      "articles": [
        {
          "number": "1",
          "title": "Actual heading only",
          "text": "Prose directly under the article and outside clauses",
          "clauses": [
            {
              "number": "1",
              "text": "Prose directly under the clause and outside points",
              "points": [
                {
                  "label": "a",
                  "text": "Point content",
                  "children": []
                }
              ]
            }
          ],
          "points": []
        }
      ],
      "blocks": ["Unstructured but substantive source text"]
    }
  ]
}
```

## Inheritance

A descendant inherits all ancestors. The path to a point is sufficient context:

```text
document number/title
→ part title/reference
→ chapter number/title
→ section number/title
→ article number/title
→ clause number
→ point label
```

Do not copy this path into the descendant's `text`. Construct it only when producing training examples or retrieval chunks.

## Boundary rules

- `title` contains only a real printed heading. If the source has `Điều 1. Ban hành kèm theo...` with no separate heading, omit `title` and store the sentence in `text`.
- `text` retains source wording but omits the structural prefix already encoded in `number` or `label`.
- Points directly under an article belong in `article.points`; points under a clause belong in `clause.points`.
- Text before the first clause belongs to `article.text`. Text before the first point belongs to `clause.text`.
- An attachment begins a new part and keeps its attachment reference and internal numbering, even when numbering restarts at Điều 1.
- Tables, forms, schedules, signatures with legal fields, or material that cannot be represented safely go into `blocks` without summarization.

## Important-token audit

Compare source and reconstructed content for at least:

- all `Điều`, `Khoản`, `điểm` references and their numbers/labels;
- `không`, `trừ`, `ngoại trừ`, `chỉ`, `phải`, `được`, `cấm`;
- dates, durations, deadlines, ages, quantities, percentages and monetary amounts;
- document identifiers such as `36/2012/QĐ-TTg`;
- named agencies, regulated subjects and geographic scope;
- amendment, replacement, repeal, transition and effective-date language.

Whitespace normalization is allowed. Any other difference requires human review.

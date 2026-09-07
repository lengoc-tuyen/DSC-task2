---
name: vietnamese-legal-corpus-curator
description: Curate raw Vietnamese legal-document JSON into a compact inherited legal tree for fine-tuning while preserving every substantive statement, citation, date, amount, condition, exception, and Điều/Khoản/Điểm relationship. Use when converting context_*.json corpus files, not for answering legal questions.
---

# Vietnamese Legal Corpus Curator

Produce a static, human-audited JSON document for fine-tuning. Optimize repetition only after proving that substantive content is preserved.

## Portability

Do not assume a repository layout, working directory, filename convention, or `outputs/` folder. Resolve the source and destination from the paths or attachments supplied in the current request. Relative links inside this skill are only skill resources, not corpus paths. The user can copy this entire skill directory to another machine or project and provide different input/output paths without changing the schema or validation rules.

## Required references

Read [schema.md](references/schema.md) before editing. Use [prompt.md](references/prompt.md) when the user needs a reusable prompt or when processing another batch.

## Non-negotiable invariants

1. Treat the source `passage` as authoritative. Never infer, summarize, modernize, correct, translate, or complete legal wording from outside knowledge.
2. Preserve verbatim all substantive text, including dates, document numbers, organizations, definitions, duties, rights, prohibitions, conditions, exceptions, cross-references, sanctions, amounts, percentages, deadlines, transition clauses, and effective dates.
3. Preserve every structural label and its correct parent: phần/quyển/chương/mục/tiểu mục/điều/khoản/điểm and appendices or forms.
4. Remove only administrative masthead/footer material that has no legal effect: national header, motto, separator rules, distribution list, copy count, storage notation, signature title, and signer name. Do not remove issuing agency, document number, place/date, title, legal bases, proposal, enactment formula, effective date, or attachment reference.
5. Parent context is inherited. Do not repeat document, part, chapter, section, or article headings inside descendant text.
6. Removing repeated labels is allowed only when represented losslessly by fields such as `number` or `label`. Example: store Khoản `1. Nội dung` as `{ "number": "1", "text": "Nội dung" }`.
7. If a boundary is ambiguous, preserve the entire original text in the nearest safe `text` or `blocks` field and record the ambiguity for review. Never guess and never drop it.

## Workflow

1. Read the complete source, including the beginning, transition into attachments, and ending.
2. Inventory expected counts and sequences for parts, chapters, sections, articles, clauses, and points. Record missing, duplicated, lettered, or non-contiguous labels as source facts rather than renumbering them.
3. Separate metadata, preamble, operative decision, attachments, and administrative footer.
4. Build the tree manually according to `schema.md`. Keep actual article headings in `title`; put operative prose in `text`. An Điều in an amending/issuing decision often has no title and must use `text` only.
5. Join OCR line wraps only. Preserve punctuation, list boundaries, paragraph meaning, and the original order.
6. Deduplicate only ancestor context and structural prefixes. Never deduplicate repeated wording inside the law because repetition may carry legal meaning.
7. Validate before writing the final file:
   - Compare every source legal basis with `legal_bases`, in order.
   - Compare every proposal and enactment formula.
   - Verify every structural label and parent path.
   - Reconstruct each Điều from `title`, `text`, clauses, and points; normalized for whitespace only, it must equal the corresponding substantive source text.
   - Check exact preservation of all important tokens listed in `schema.md`.
   - Confirm removed text belongs exclusively to the permitted administrative set.
   - Report source count, output count, and mismatch count for legal bases and every structural level. Direct source-to-output comparison is mandatory regardless of where either file is stored.
8. Write readable UTF-8 JSON with `ensure_ascii=false` semantics and two-space indentation. Do not include analysis, confidence scores, parser artifacts, offsets, hashes, or duplicated full passage in the output.

## Acceptance rule

Do not report success merely because JSON parses or counts match. Success requires zero unexplained content mismatch after reconstruction. If exact preservation cannot be established, mark the file as requiring review and identify the precise source span; do not present it as completed.

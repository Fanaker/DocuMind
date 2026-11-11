# DocuMind — release checklist

**Version:** 1.0.0  
**Date:** 2026-11-11  
**Scope:** Fully local, extractive document search / traditional ML prototype.

## Verified in the creation environment
- Five Pytest cases passed: grounded answer, unsupported question, evaluation, upload validation and health.
- Six sample evaluation prompts matched expected facts and their primary documents.
- JavaScript parser check passed.
- Four screenshot views rendered with API-generated content.

## Real functions
- TF-IDF feature extraction, cosine similarity, weighted section ranking, extractive sentence selection and source references.
- User-uploaded UTF-8 .md/.txt files are indexed locally.
- Unsupported questions trigger an abstention message.

## Limits
- No LLM, hosted AI or neural embedding system; do not advertise generative RAG.
- The displayed confidence is a heuristic retrieval strength score, not a calibrated probability.
- Example company policies are fictitious and not legal or HR advice.

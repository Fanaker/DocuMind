# Retrieval design notes

The Markdown corpus is split by level-two headings and indexed with scikit-learn's TF-IDF vectorizer. Query normalization removes accent marks and common Spanish stop words; a small alias map handles frequent variants. Cosine similarity ranks candidates, adjusted by heading and vocabulary overlap. Unsupported or insufficiently matched questions are rejected instead of guessed.

The answer is selected as an extractive sentence from the best-matching section; citations include document, heading and excerpt. This is not a neural embedding model, not a generative chatbot and not a production-ready legal/document-management tool.

## Evaluation
Six reference prompts in `app/main.py` check for an expected phrase and the correct top document. The evaluation is intentionally limited and dataset-dependent. Test on a broader and independently labeled corpus before making performance claims.

## Potential improvements
1. Better Spanish lemmatization and morphological normalization.
2. Hold-out evaluation cases, recall@k / MRR and error analysis.
3. Stronger document access controls and upload restrictions.
4. Optional open-weight embedding model and hybrid retrieval.
5. Optional LLM answer synthesis only when explicitly configured, with evidence gates and citations.

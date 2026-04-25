# Enterprise Knowledge Skill

## Purpose

Use this skill to query the local enterprise knowledge agent and to register distribution targets for a tracked Feishu document.

This skill is a thin HTTP wrapper around the backend.
It must not contain business logic.
It only calls the backend endpoints described below.

## Base URL

Set `BASE_URL` to the running backend service, for example:

- `http://127.0.0.1:8000`

## Endpoint 1: Query enterprise knowledge

- **Method**: `POST`
- **URL**: `${BASE_URL}/api/openclaw/query`
- **When to use**:
  - The user asks a question about company knowledge, rules, process, or documentation.
  - The answer should be grounded in the indexed local document corpus.

### Request body

```json
{
  "question": "差旅报销流程是什么？",
  "subdirectory": "lark_docs",
  "top_k": 5,
  "retrieval_mode": "hybrid"
}
```

### Expected response fields

- `answer`
- `citations`
- `retrieval_mode`
- `document_count`

## Endpoint 2: Save distribution targets for a document

- **Method**: `POST`
- **URL**: `${BASE_URL}/api/openclaw/subscribe`
- **When to use**:
  - The user wants a document to notify specific chats or users when content changes.
  - The tool should persist the targets into the document metadata.

### Request body

```json
{
  "doc_id": "doccnxxxx",
  "subdirectory": "lark_docs",
  "replace_existing": false,
  "source": "openclaw",
  "targets": [
    {
      "target_type": "chat",
      "target_id": "oc_xxx",
      "target_name": "产品群"
    }
  ]
}
```

### Expected response fields

- `doc_id`
- `metadata_path`
- `target_count`
- `replaced_existing`

## Constraints

- Do not implement retrieval, ranking, or distribution logic inside the skill.
- Do not call Feishu APIs directly from the skill.
- If the backend returns an error, surface the error message instead of guessing.

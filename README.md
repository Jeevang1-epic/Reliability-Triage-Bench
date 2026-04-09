---
title: Reliability Triage Bench
sdk: docker
app_port: 8000
colorFrom: gray
colorTo: blue
pinned: false
tags:
  - openenv
---

# Reliability Triage Bench

`reliability_triage_env` is an OpenEnv benchmark for incident-response triage in production systems.  
The agent must investigate operational signals, classify the incident, assign ownership, choose mitigation, and submit a structured triage decision.

This benchmark is designed for real-world agent evaluation:
- It models an actual on-call workflow used in platform, payments, and security operations.
- It contains deterministic graders and explicit difficulty progression.
- It provides dense rewards for partial progress, not only terminal pass/fail.

## What This Submission Includes

- Full OpenEnv API compliance (`step()`, `reset()`, `state()`, typed models, `openenv.yaml`)
- 3 deterministic graded tasks (`easy`, `medium`, `hard`)
- Reward shaping with progress signals and penalties for poor interaction patterns
- Root-level `inference.py` with strict `[START]`, `[STEP]`, `[END]` logging format
- Dockerized runtime for Hugging Face Space deployment
- Local validation script and tests

## Task Set

1. `easy_api_latency_spike` (easy)  
Objective: classify a post-deploy latency regression and route ownership correctly.
1. `medium_payment_processor_outage` (medium)  
Objective: handle external dependency outage with routing, failover, and escalation.
1. `hard_credential_compromise` (hard)  
Objective: contain an active credential compromise and trigger compliance workflow.

Each task has:
- deterministic expected field outputs
- deterministic keyword-based note scoring
- score normalized to `[0.0, 1.0]`

## Action Space

`ReliabilityTriageAction` fields:
- `command`: one of `view_brief | view_signal | set_field | append_note | submit`
- `field`: decision field name for `set_field`
- `value`: decision value for `set_field`
- `signal_id`: signal identifier for `view_signal`
- `note`: triage note text for `append_note`

## Observation Space

`ReliabilityTriageObservation` fields:
- `task_name`, `difficulty`
- `incident_title`, `incident_summary`
- `visible_signals`
- `available_fields`
- `decisions`
- `note`
- `checklist_progress` (running normalized score)
- `remaining_steps`
- `last_feedback`
- standard OpenEnv fields: `reward`, `done`, `metadata`

## State Space

`ReliabilityTriageState` fields:
- `episode_id`, `step_count`
- `task_name`, `difficulty`
- `max_steps`
- `submitted`
- `score`
- `invalid_actions`

## Reward and Grading

Reward shaping combines:
- progress toward correct field submissions
- note-quality gains via required keyword coverage
- penalties for invalid commands, repeated actions, and step usage

Final task score is deterministic:
- weighted field accuracy
- keyword coverage for triage note
- clamped to `[0, 1]`

Success thresholds:
- easy: `>= 0.85`
- medium: `>= 0.80`
- hard: `>= 0.75`

## Project Structure

```text
.
├── __init__.py
├── client.py
├── models.py
├── task_bank.py
├── inference.py
├── openenv.yaml
├── pyproject.toml
├── Dockerfile
├── server
│   ├── app.py
│   ├── reliability_triage_environment.py
│   └── requirements.txt
├── scripts
│   └── validate-submission.sh
└── tests
    ├── test_environment.py
    └── test_task_bank.py
```

## Local Setup

```bash
python -m pip install -e .
```

Run server:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Validate environment structure:

```bash
openenv validate
```

## Docker Build and Run

```bash
docker build -t reliability-triage-env:latest .
docker run --rm -p 8000:8000 reliability-triage-env:latest
```

## Baseline Inference Script

The root `inference.py` is submission-ready and follows the required logging contract.

Mandatory environment variables:
- `API_BASE_URL`: LLM endpoint URL
- `MODEL_NAME`: model identifier
- `HF_TOKEN`: API key/token for model access

Optional:
- `LOCAL_IMAGE_NAME`: local docker image name for `from_docker_image()` flow
- `ENV_BASE_URL`: direct server URL fallback (default: `http://localhost:8000`)
- `TASKS`: comma-separated task list

Run:

```bash
python inference.py
```

The script prints:
- `[START] ...`
- one `[STEP] ...` per environment step
- `[END] ...` exactly once per task

## Hugging Face Space Deployment

This repository is Docker-space ready:
- `sdk: docker` in README metadata
- root `Dockerfile`
- OpenEnv `openenv.yaml`

Deploy through OpenEnv:

```bash
openenv push
```

## Submission Precheck

```bash
bash scripts/validate-submission.sh https://<your-space>.hf.space .
```

This precheck runs:
1. `/reset` ping check
1. local `docker build`
1. `openenv validate`

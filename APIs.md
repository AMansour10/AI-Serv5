# AI Career Coach API

## Primary Endpoint
POST /api/career-coach

## Backward-Compatible Endpoint (Deprecated)
POST /api/career-coach/{employee_id}
- Query parameter: `period` (optional)
*(Deprecated: Preserved for backward compatibility. New integrations must use `POST /api/career-coach` with a JSON request body).*

## Input Data Type
- employee_id: string
- period: string | null

## Input Shape
```json
{
  "employee_id": "EMP-SEC-ALICE",
  "period": "2026-Q3"
}
```

## Error Handling
Returns `HTTP 502 Bad Gateway` on AI provider or service failures with a safe reference ID:
```json
{
  "detail": "AI service temporarily unavailable. Reference ID: 7b845890-410a-4286-bc94-469b76c9ad24"
}
```

## Output Shape
```json
{
  "status": "success",
  "employee_id": "EMP-SEC-ALICE",
  "strengths": [
    {
      "title": "High Performance Delivery",
      "description": "Consistently exceeds performance targets with top scores across key metrics.",
      "evidence": [
        {
          "source_type": "performance",
          "source_id": 1,
          "claim": "Overall performance score of 93.5 in Q3 2026"
        }
      ]
    }
  ],
  "development_areas": [
    {
      "title": "Increase Knowledge Sharing Sessions",
      "description": "Conduct regular knowledge sharing to mentor junior peers.",
      "evidence": [
        {
          "source_type": "evaluation_theme",
          "source_id": 1,
          "claim": "Feedback highlighted opportunity to mentor junior peers"
        }
      ],
      "priority": "high"
    }
  ],
  "development_plan": [
    {
      "action": "Schedule monthly knowledge sharing sessions",
      "reason": "Leverage mentorship strengths and address identified opportunity",
      "measurable_target": "Conduct at least 3 sessions by end of quarter",
      "suggested_timeline": "First session within 2 weeks"
    }
  ],
  "follow_up": {
    "checkpoint": "2026-11-15",
    "review_focus": "Review effectiveness and attendance of knowledge sharing sessions"
  },
  "created_at": "2026-09-08T18:30:00Z"
}
```

## Insufficient Data Output
```json
{
  "status": "insufficient_data",
  "employee_id": "EMP-SEC-ALICE",
  "missing_categories": [
    "performance",
    "goals"
  ],
  "message": "Not enough approved employee data to generate a reliable career coaching plan.",
  "created_at": "2026-09-08T18:30:00Z"
}
```

---

# AI HR Policy Assistant API

## Endpoint
POST /api/policy-assistant

## Input Data Type
- employee_id: string (required)
- question: string (required)
- session_id: string | null (optional; if omitted, a new chat session is automatically created)

## Input Shape
```json
{
  "employee_id": "EMP-SEC-ALICE",
  "question": "What is the annual leave rollover limit?",
  "session_id": "8f3b2a4c-5678-4321-9876-abcdef012345"
}
```

## Error Handling
- `HTTP 404 Not Found`: Returned when the specified `session_id` does not exist:
  ```json
  {
    "detail": "Chat session not found."
  }
  ```
- `HTTP 403 Forbidden`: Returned when an employee attempts to access a session belonging to a different employee:
  ```json
  {
    "detail": "Access denied: session belongs to another employee."
  }
  ```
- `HTTP 502 Bad Gateway`: Returned on AI provider or service failures with a safe reference ID:
  ```json
  {
    "detail": "AI service temporarily unavailable. Reference ID: 7b845890-410a-4286-bc94-469b76c9ad24"
  }
  ```

## Output Data Type
- status: string
- session_id: string
- employee_id: string
- answer: string
- policy_references: array
- employee_facts_used: array
- created_at: datetime

## Output Shape
```json
{
  "status": "success",
  "session_id": "8f3b2a4c-5678-4321-9876-abcdef012345",
  "employee_id": "EMP-SEC-ALICE",
  "answer": "Employees may carry forward up to five (5) unused annual leave days into the next calendar year.",
  "policy_references": [
    {
      "policy_id": 1,
      "policy_code": "POL-LEAVE-001",
      "title": "Annual Leave & Time Off Policy",
      "version": "1.0"
    }
  ],
  "employee_facts_used": [],
  "created_at": "2026-09-09T09:50:31Z"
}
```

## Unsupported Question Output
```json
{
  "status": "unsupported",
  "session_id": "8f3b2a4c-5678-4321-9876-abcdef012345",
  "employee_id": "EMP-SEC-ALICE",
  "message": "No approved company policy category matches this inquiry.",
  "created_at": "2026-09-09T09:50:32Z"
}
```

---

## Conversation Memory & Token Optimization Architecture

The AI HR Policy Assistant maintains multi-turn conversation memory efficiently without unbounded token growth:

1. **Recent-Message Window (Max 4 Messages)**:
   - For an ongoing session, only the last **4 prior messages** (up to 2 user + 2 assistant turns) are directly injected into the prompt inside `<RECENT_CONVERSATION_HISTORY>`.
   - **Full conversation history is NEVER forwarded to Groq**, guaranteeing predictable latency and low token costs regardless of how long the chat runs.

2. **Rolling Conversation Summary**:
   - When a conversation exceeds the 4-message window, older messages are compressed into a compact, 1–2 sentence summary (maximum 60 words) stored in `ChatSession.summary`.
   - The summary is injected into the prompt inside `<CONVERSATION_SUMMARY>`.
   - To minimize token usage and avoid unnecessary API calls, the summary is updated incrementally in 4-message batches rather than on every request.

3. **Follow-Up Understanding**:
   - Both category classification and the policy answer prompt receive the recent conversation context to resolve pronouns and follow-up inquiries (e.g. *"Does that apply to me too?"*).
   - **Grounding Safety**: Past conversation turns are treated strictly as inert context. All policy claims and numeric values must still be independently grounded in currently approved company policies.

---

# AI Performance Insight Generator API

## Endpoint
POST /api/performance-insight

## Purpose
Generates structured, evidence-based comparative performance insights across evaluation periods for an employee. Computes deterministic metric trends and pairs them with AI-synthesized qualitative interpretation and actionable follow-up review steps.

## Input Data Type
- employee_id: string (required)
- period: string | null (optional; if omitted, the latest approved evaluation period is compared against the preceding approved period)

## Input Shape
```json
{
  "employee_id": "EMP-SEC-ALICE",
  "period": "2026-Q2"
}
```

## Error Handling
- `HTTP 422 Unprocessable Entity`: Returned on invalid request payload (e.g. missing `employee_id`, empty strings, or unrecognized/unexpected fields).
- `HTTP 502 Bad Gateway`: Returned on AI provider or service failures with a safe reference ID without exposing internal implementation details:
  ```json
  {
    "detail": "AI service temporarily unavailable. Reference ID: 7b845890-410a-4286-bc94-469b76c9ad24"
  }
  ```

## Output Data Type
- status: string (`"success"` | `"insufficient_data"`)
- employee_id: string
- verified_facts: object (authoritative metrics retrieved from approved database records)
- calculated_trends: object (deterministic mathematical trends computed across periods)
- ai_interpretation: object (qualitative analysis: summary, what improved, what declined, contributing indicators)
- suggested_review_actions: array (actionable follow-up review steps for managers/leads)
- created_at: datetime

## Output Shape
```json
{
  "status": "success",
  "employee_id": "EMP-SEC-ALICE",
  "verified_facts": {
    "target_period": "2026-Q2",
    "comparison_period": "2026-Q1",
    "metrics_by_period": [
      {
        "period": "2026-Q1",
        "overall_score": 82.0,
        "task_completion_rate": 85.0,
        "goal_achievement_rate": 80.0,
        "attendance_rate": 96.0
      },
      {
        "period": "2026-Q2",
        "overall_score": 88.0,
        "task_completion_rate": 92.0,
        "goal_achievement_rate": 86.0,
        "attendance_rate": 90.0
      }
    ]
  },
  "calculated_trends": {
    "from_period": "2026-Q1",
    "to_period": "2026-Q2",
    "metrics": {
      "overall_score": {
        "metric_name": "overall_score",
        "previous_value": 82.0,
        "current_value": 88.0,
        "delta": 6.0,
        "direction": "improved",
        "percent_change": 7.32
      },
      "task_completion_rate": {
        "metric_name": "task_completion_rate",
        "previous_value": 85.0,
        "current_value": 92.0,
        "delta": 7.0,
        "direction": "improved",
        "percent_change": 8.24
      },
      "goal_achievement_rate": {
        "metric_name": "goal_achievement_rate",
        "previous_value": 80.0,
        "current_value": 86.0,
        "delta": 6.0,
        "direction": "improved",
        "percent_change": 7.5
      },
      "attendance_rate": {
        "metric_name": "attendance_rate",
        "previous_value": 96.0,
        "current_value": 90.0,
        "delta": -6.0,
        "direction": "declined",
        "percent_change": -6.25
      }
    },
    "improved_metrics": ["overall_score", "task_completion_rate", "goal_achievement_rate"],
    "declined_metrics": ["attendance_rate"],
    "stable_metrics": []
  },
  "ai_interpretation": {
    "summary": "Overall score increased from 82.0 to 88.0 across 2026-Q1 and 2026-Q2, showing solid delivery progress.",
    "improvements": [
      {
        "metric": "overall_score",
        "summary": "Overall score improved by 6.0 points from 82.0 to 88.0.",
        "contributing_indicators": [
          {
            "indicator_name": "Project throughput",
            "category": "tasks",
            "observation": "Observed increased task completion across key assignments to review."
          }
        ]
      }
    ],
    "declines": [
      {
        "metric": "attendance_rate",
        "summary": "Attendance rate declined by 6.0 points from 96.0 to 90.0.",
        "contributing_indicators": [
          {
            "indicator_name": "Shift schedule variance",
            "category": "attendance",
            "observation": "Schedule changes during period may warrant review alongside performance metrics."
          }
        ]
      }
    ]
  },
  "suggested_review_actions": [
    {
      "priority": "medium",
      "focus_area": "Attendance and Delivery Balance",
      "recommended_action": "Review shift scheduling during upcoming bi-weekly 1-on-1 check-in.",
      "rationale": "High task throughput indicates strong execution despite attendance rate variance."
    }
  ],
  "created_at": "2026-09-13T19:40:00Z"
}
```

## Insufficient Data Output
Returned when an employee does not exist, has zero approved performance records, or only has a single approved period (at least two periods are required for comparative trends):
```json
{
  "status": "insufficient_data",
  "employee_id": "EMP-SEC-ALICE",
  "reason": "Only one approved performance period available; cross-period comparative trend requires at least two periods.",
  "periods_found": [
    "2026-Q1"
  ],
  "message": "Insufficient approved performance data to generate comparative performance insights.",
  "created_at": "2026-09-13T19:40:00Z"
}
```

---

## Grounding, Safety & Governance Architecture

1. **Approved-Data Boundary**:
   - Only performance records with `is_approved == True` are queried and analyzed.
   - Unapproved records, drafts, or records belonging to other employees are strictly excluded and never exposed.

2. **Clear Separation of Facts, Trends, and AI Interpretation**:
   - `verified_facts` and `calculated_trends` are assembled authoritatively by the backend application data layer. The LLM is never permitted to invent or alter factual metrics, periods, scores, or trend directions.
   - `ai_interpretation` contains purely qualitative analysis and observed context to review.

3. **Causal Safety (Non-Causal Contributing Indicators)**:
   - **Contributing indicators are NOT confirmed causes**: They represent observed operational correlations and context factors to review, never verified root causes.
   - The service strictly rejects output containing definitive, unverified causal assertions (e.g. *"the root cause is"* or *"definitely caused by"*).

4. **Prohibition of Employment Decisions**:
   - The AI is strictly prohibited from recommending or deciding termination, hiring, firing, promotions, demotions, salary/wage adjustments, bonuses, disciplinary actions, or performance improvement plans (PIPs).
   - Recommendations are restricted to managerial check-ins, mentoring, review steps, or workload calibrations.

5. **Fail-Closed Resilience**:
   - Insufficient data cases fail closed immediately without invoking the external LLM.
   - Provider errors, timeouts, malformed JSON, and grounding validation failures fail safely and return HTTP 502 with an opaque reference ID.

---

# AI Evaluation Draft Assistant API

## Endpoint
POST /api/evaluation-draft

## Input Data Type
- employee_id: string (required)
- period: string (required, e.g. "2026-Q3")
- evaluation_scores: object | null (optional dictionary of metric scores, e.g. `{"overall_score": 88.0, "leadership": 85.0}`)
- manager_notes: string | null (optional manager observations or notes, max 3000 chars)

## Input Shape
```json
{
  "employee_id": "EMP-SEC-ALICE",
  "period": "2026-Q3",
  "evaluation_scores": {
    "overall": 92.0,
    "leadership": 88.0
  },
  "manager_notes": "Demonstrated exceptional technical leadership during the platform migration."
}
```

## Success Response (`200 OK`)
```json
{
  "status": "success",
  "employee_id": "EMP-SEC-ALICE",
  "period": "2026-Q3",
  "evaluation_narrative": "Alice delivered exemplary technical performance during Q3 2026, achieving a 94.0 overall score and successfully guiding the core cutover without service disruption. Her systems architecture work and mentorship of junior engineers represent standout contributions.",
  "strengths": [
    {
      "title": "High Delivery Quality and Architecture Execution",
      "description": "Consistently delivered robust systems with zero errors during production migration.",
      "evidence": [
        {
          "source_type": "performance",
          "source_id": 1,
          "claim": "Achieved overall score of 94.0 and 97.0% task completion in Q3 2026"
        }
      ]
    }
  ],
  "improvement_areas": [
    {
      "title": "Knowledge Sharing and Architecture Walkthroughs",
      "description": "Conduct monthly architecture review sessions for junior engineers to scale domain expertise.",
      "evidence": [
        {
          "source_type": "evaluation_theme",
          "source_id": 1,
          "claim": "Feedback highlighted opportunity to run more knowledge sharing sessions"
        }
      ],
      "priority": "medium"
    }
  ],
  "entered_scores": {
    "overall": 92.0,
    "leadership": 88.0
  },
  "human_review_required": true,
  "review_disclaimer": "This evaluation is an AI-generated draft intended solely to assist manager review. A human manager must review, edit, and approve this evaluation before any official use or persistence.",
  "created_at": "2026-09-14T11:00:00Z"
}
```

## Insufficient Data Output (`200 OK`)
Returned immediately when the target employee has zero approved records or lacks the minimum baseline data categories (at least one approved performance record and at least one goal, task outcome, or evaluation theme):
```json
{
  "status": "insufficient_data",
  "employee_id": "EMP-EMPTY",
  "period": "2026-Q3",
  "missing_categories": [
    "performance",
    "goals",
    "skills",
    "task_outcomes",
    "evaluation_themes"
  ],
  "message": "Not enough approved employee data to generate a reliable evaluation draft.",
  "human_review_required": false,
  "created_at": "2026-09-14T11:00:00Z"
}
```

## Error Handling
- **`422 Unprocessable Entity`**: Returned when required fields (`employee_id`, `period`) are missing, invalid, or scores are out of bounds (0.0 to 100.0).
- **`502 Bad Gateway`**: Returned on AI provider failures, timeouts, or ungrounded model outputs, with an opaque reference ID:
```json
{
  "detail": "AI service temporarily unavailable. Reference ID: 3a2c5b98-e04f-4d3a-86c2-123456789abc"
}
```

## Governance & Safety Guarantees
1. **Stateless Draft Guarantee (No Automatic Persistence)**:
   - The endpoint generates an in-memory draft evaluation returned directly to the caller.
   - It **never** writes or submits permanent records to `performance_records`, `evaluation_themes`, or any database table.
   - Human manager review and explicit approval is strictly required before any future persistence.
2. **Absolute Prohibition on Automated Employment Decisions**:
   - The AI assistant is strictly prohibited by deterministic safety filtering from recommending hiring, firing, promotion, demotion, salary/wage adjustments, bonuses, compensation, disciplinary actions, or performance improvement plans (PIPs).
3. **Approved-Only Evidence Grounding**:
   - The context builder queries only approved records (`is_approved == True`).
   - Every cited strength or improvement area must reference explicit source records by `source_type` and `source_id`.
   - Numeric claims are cross-checked against source records to eliminate hallucinations.
4. **Prompt Injection Protection**:
   - All untrusted input fields and context tags are sanitized to prevent delimiter breakout or prompt override attempts.


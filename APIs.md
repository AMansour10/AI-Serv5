# AI Career Coach API

## Endpoint
POST /api/career-coach/{employee_id}

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

## Output Data Type
- status: string
- employee_id: string
- strengths: array
- development_areas: array
- development_plan: array
- follow_up: object
- created_at: datetime

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

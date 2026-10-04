```mermaid
flowchart LR
   A[Budget] --> C[Variance Engine]
   B[Actuals] --> C
   C --> D[Variance Review]
   E[Scenario Assumptions] --> F[12-Month Forecast]
   D --> G[Management Report]
   F --> G
```

## Deliverables

| Output         | Purpose                    |
| -------------- | -------------------------- |
| `variance.csv` | Budget vs. actual analysis |
| `forecast.csv` | 12-month driver forecast   |
| `report.html`  | Management-facing report   |
| `DEMO.md`      | Walkthrough                |

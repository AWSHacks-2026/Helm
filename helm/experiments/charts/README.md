# ShopFix demo charts

Generated from demo matrix (intent opposition excluded).

Source: `experiments/results/shopfix_demo_matrix_20260517_091231.json`

| Chart | Use in demo |
|-------|-------------|
| [00_dashboard.png](00_dashboard.png) | Single-slide overview |
| [01_contention_savings.png](01_contention_savings.png) | Cost + wall % by N |
| [02_contention_absolute.png](02_contention_absolute.png) | Absolute $ and seconds |
| [03_contention_agents.png](03_contention_agents.png) | Fewer agents run |
| [04_merge_fleet_wall.png](04_merge_fleet_wall.png) | Merge parallelism story |
| [05_contention_phases.png](05_contention_phases.png) | Where time goes |
| [06_guardrail_savings.png](06_guardrail_savings.png) | Guardrail savings per trial |
| [07_guardrail_absolute.png](07_guardrail_absolute.png) | Guardrail $ and seconds (median) |
| [08_guardrail_calls.png](08_guardrail_calls.png) | 2 Haiku vs 1 guardrail call |
| [09_guardrail_headline.png](09_guardrail_headline.png) | Guardrail one-slide |

Regenerate:

```bash
python scripts/plot_shopfix_demo_matrix.py
bash scripts/sync_demo_charts.sh
```

Charts marked above are copied into `helm/frontend/public/demo-charts/` for the **Demo Charts** view in the Control Tower UI.

# HW9 - Whole-system design and retraining DAG

Two-part system design: comparing ML pipeline and retraining architectures, then an Airflow DAG for retail inventory forecasting.

## Stack

Apache Airflow (AWS S3 provider, branching, TaskGroups), MLflow registry, scikit-learn (LinearRegression), pandas, numpy, Terraform, GitHub Actions, Docker Compose.

## Assignment

Part 1 compares ML pipeline architectures and retraining triggers across four cases. Part 2 designs and writes an Airflow DAG that computes warehouse stock for a retail chain: wait on S3 then branch on a retrain decision then a training TaskGroup then compare against production then promote in MLflow. The folder also carries the Terraform infra and IaC GitHub Actions workflows for the design.

## Files

| File | Description |
|------|-------------|
| `ML-HW_9-main/` | Project: design notebook, Airflow DAG, Terraform `infra/`, IaC workflows |
| `ML-HW_9-main/HW9_Design_Вольхин_Сергей.ipynb` | Main solution notebook (architecture comparison + DAG) |

The original `ML-HW_9-main.zip` submission archive stays in the folder but is excluded from git.

## Notes

I kept all configuration as constants at the top of the DAG so there are no magic numbers buried in the tasks. The retrain step is a branch operator: skip training entirely when the data has not moved enough, which felt closer to how a cost-conscious pipeline actually behaves.

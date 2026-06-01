# HW7 - CI/CD pipeline with canary and blue-green

A FastAPI iris classifier shipped through GitLab CI and GitHub Actions with canary, blue-green, and A/B rollout.

## Stack

Python, FastAPI 0.115, scikit-learn 1.5.2, Pydantic, GitHub Actions, GitLab CI, Docker Compose, nginx (`split_clients`), pytest, ruff.

## Assignment

Build a CI/CD pipeline for an ML service and demonstrate safe rollout. I set up lint/test/train/build stages, two image versions (v1.0.0 and v1.1.0), nginx-based canary (10 to 25 to 50 to 100 percent) and blue-green switching, an A/B test plan, and auto-rollback on a failed health check. Architecture Decision Records justify canary over blue-green.

## Files

| File | Description |
|------|-------------|
| `ML-HW_7-main/` | Main project: `app/`, `docker/`, `scripts/`, `.github/workflows/`, `.gitlab-ci.yml`, tests, ADRs |
| `ML-HW_7-main/HW7_CICD_Volkhin_Sergei.ipynb` | Solution notebook |
| `Развертывание ML моделей_ Домашнее задание 7. Сборка конвейера CI_CD.pdf` | Assignment specification |

Full project writeup: [`ML-HW_7-main/README.md`](ML-HW_7-main/README.md).

## Notes

The notebook has no outputs because the real run happens in CI, not Jupyter. The pipeline logs and the `pipeline_metadata.json` (pip freeze, git SHA, dataset and model sha256) are the actual evidence. Pinning every version was tedious, but that is the whole point of reproducibility.

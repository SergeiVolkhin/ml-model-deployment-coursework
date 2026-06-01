# HW3 - Infrastructure as Code

Fixing and validating a broken OpenTofu / Terraform configuration, plus the declarative IaC workflow.

## Stack

OpenTofu (Terraform), Ansible, YAML, Python 3 (`pyyaml`, `IPython.display`).

## Assignment

The core task was to take an intentionally broken OpenTofu config and get it to validate and plan cleanly, and to cover configuration management with Ansible alongside it. I worked through the errors one at a time and documented the validate then plan loop.

## Files

| File | Description |
|------|-------------|
| `HW3_iac_Вольхин_Сергей.ipynb` | Main solution notebook (IaC fixes + validation) |
| `Развертывание ML моделей_ Домашнее задание 3. Облачная инфраструктура.pdf` | Assignment specification |

## Notes

Most of the time went into reading OpenTofu's error messages carefully. Half of them pointed at the wrong line, so I learned to trust `tofu validate` over the inline hints.

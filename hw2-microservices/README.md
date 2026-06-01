# HW2 - Monolith vs microservices

An architecture study comparing a monolith against a microservice split, documented with diagrams-as-code.

## Stack

Python 3, `diagrams` (Graphviz), pandas, scikit-learn, `IPython.display`.

## Assignment

Required to reason about when to split a monolith into microservices and when to leave it alone. I drew several deployment topologies with the `diagrams` library (Postgres, Redis, RabbitMQ, Kafka, Nginx, Prometheus/Grafana, managed RDS) and wrote up the trade-offs - scaling pressure, team boundaries, deployment cost - rather than shipping a running service.

## Files

| File | Description |
|------|-------------|
| `HW2_microservices_Вольхин_Сергей.ipynb` | Main solution notebook (diagrams + written analysis) |
| `Развертывание ML моделей_ Домашнее задание 2. Микросервисная архитектура.pdf` | Assignment specification |

## Notes

This one is mostly judgement, not code. The `diagrams` library was the only real dependency, and getting Graphviz to render on Windows took longer than the actual analysis did.

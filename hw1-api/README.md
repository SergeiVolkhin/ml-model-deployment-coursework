# HW1 - REST API fundamentals with FastAPI

Building an HTTP API from the standard library up to FastAPI, then consuming it as a client.

## Stack

Python 3, FastAPI, Uvicorn, Pydantic, `requests`, built-in `http.server` / `socketserver`, pandas.

## Assignment

The task was to understand HTTP APIs end to end. First implement a minimal server with the standard-library `http.server`, then talk to it over HTTP with the `requests` client, and finally rebuild the same surface on FastAPI with Pydantic models and concurrent request handling. I built both halves: a hand-rolled CRUD handler and the FastAPI version with validation.

## Files

| File | Description |
|------|-------------|
| `Вольхин_Сергей_Александрович.ipynb` | Main solution notebook (server + client, `http.server` to FastAPI) |
| `Развертывание ML моделей_ Домашнее задание 1. Знакомство с API.pdf` | Assignment specification |
| `Дополнительная информация FastAPI.txt` | Course notes on FastAPI |

## Notes

The starter server is deliberately written in an old `http.server` style, which threw me at first. I kept reaching for FastAPI idioms before I realized the point was to feel the low-level pain before the framework hides it.

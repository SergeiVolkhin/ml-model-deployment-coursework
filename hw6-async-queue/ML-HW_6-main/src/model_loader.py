"""Lazy-загрузка эмбеддера с прогревом.

rubert-tiny2 поднимается при первом обращении, но в проде дергаем warmup() в
lifespan консьюмера, чтобы первый юзер не ждал инициализацию.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

log = logging.getLogger(__name__)

DEFAULT_MODEL = "cointegrated/rubert-tiny2"
DEFAULT_MAX_LEN = 64


class LazyModel:
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str = "cpu",
        max_length: int = DEFAULT_MAX_LEN,
    ):
        self.model_name = model_name
        self.device = device
        self.max_length = max_length
        self._tok: Optional[AutoTokenizer] = None
        self._model: Optional[AutoModel] = None
        self._lock = threading.Lock()
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        if self._loaded:
            return
        # двойная проверка под локом - чтобы две корутины одновременно не дернули загрузку
        with self._lock:
            if self._loaded:
                return
            t0 = time.perf_counter()
            log.info("loading %s on %s", self.model_name, self.device)
            self._tok = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModel.from_pretrained(self.model_name)
            self._model.to(self.device)
            self._model.eval()
            self._loaded = True
            log.info("loaded in %.2fs", time.perf_counter() - t0)

    def warmup(self) -> None:
        # один прогон на dummy чтобы прогреть граф и получить компилированные ядра
        self.load()
        _ = self.encode(["прогрев"])
        log.info("warmup done")

    @torch.inference_mode()
    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 312), dtype=np.float32)
        self.load()
        enc = self._tok(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        ).to(self.device)
        out = self._model(**enc).last_hidden_state  # (B, T, H)
        # mean-pooling с учетом attention mask
        mask = enc["attention_mask"].unsqueeze(-1).float()
        summed = (out * mask).sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1.0)
        emb = summed / counts
        return emb.cpu().numpy().astype(np.float32)


# реестр - чтобы не плодить копии при повторных импортах
_registry: dict[str, LazyModel] = {}
_registry_lock = threading.Lock()


def get_model(name: str = DEFAULT_MODEL, device: str = "cpu") -> LazyModel:
    key = f"{name}::{device}"
    with _registry_lock:
        if key not in _registry:
            _registry[key] = LazyModel(name, device)
        return _registry[key]

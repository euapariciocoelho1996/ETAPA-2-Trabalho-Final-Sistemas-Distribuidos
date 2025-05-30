from abc import ABC, abstractmethod
from typing import Dict, Any
import time
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TimingMetrics:
    t1: float = 0.0  # Tempo de saída do cliente
    t2: float = 0.0  # Tempo de chegada no servidor
    t3: float = 0.0  # Tempo de processamento
    t4: float = 0.0  # Tempo de resposta do servidor
    t5: float = 0.0  # Tempo total

class AbstractProxy(ABC):
    def __init__(self, target_address: str):
        self.target_address = target_address
        self._request_count = 0
        self._timing_metrics = TimingMetrics()

    @property
    def request_count(self) -> int:
        return self._request_count

    def increment_request_count(self) -> None:
        self._request_count += 1

    def record_timing(self, stage: str, start_time: float = None) -> float:
        """
        Registra o tempo de uma etapa específica.
        """
        current_time = time.time()
        if start_time is None:
            start_time = current_time

        if stage == 't1':
            self._timing_metrics.t1 = current_time - start_time
        elif stage == 't2':
            self._timing_metrics.t2 = current_time - start_time
        elif stage == 't3':
            self._timing_metrics.t3 = current_time - start_time
        elif stage == 't4':
            self._timing_metrics.t4 = current_time - start_time
        elif stage == 't5':
            self._timing_metrics.t5 = current_time - start_time

        return current_time

    def get_timing_metrics(self) -> TimingMetrics:
        return self._timing_metrics

    @abstractmethod
    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método abstrato para lidar com requisições.
        Deve ser implementado pelas classes filhas.
        """
        pass 
"""Modelo predictivo con el histórico de la mina (Fase 4). Necesita numpy y scipy (extra `ml`).

`rockmasspy/__init__.py` no importa este paquete: numpy y scipy son opcionales para el resto de la librería.
"""

try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
except ImportError as e:  # pragma: no cover - el mensaje se prueba simulando la falta
    raise ImportError("rockmasspy.predictive needs numpy and scipy; "
                      "install the ml extra: pip install rockmasspy[ml]") from e

from .stats import (BayesLinearFit, BootstrapResult, DemingFit, OlsFit, bayes_linear_fit,  # noqa: E402
                    deming_fit, group_bootstrap, ols_fit)

__all__ = ["BayesLinearFit", "BootstrapResult", "DemingFit", "OlsFit", "bayes_linear_fit", "deming_fit",
           "group_bootstrap", "ols_fit"]

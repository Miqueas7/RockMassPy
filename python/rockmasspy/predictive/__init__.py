"""Modelo predictivo con el histórico de la mina (Fase 4). Necesita numpy y scipy (extra `ml`).

`rockmasspy/__init__.py` no importa este paquete: numpy y scipy son opcionales para el resto de la librería.
"""

try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
except ImportError as e:  # pragma: no cover - el mensaje se prueba simulando la falta
    raise ImportError("rockmasspy.predictive needs numpy and scipy; "
                      "install the ml extra: pip install rockmasspy[ml]") from e

from .correlations import (CORRELATION_RESULT_COLUMNS, KINDS, NO_DOMAIN, STATUSES, SiteCorrelationFit,  # noqa: E402
                           SiteCorrelationResult, fit_site_correlation, save_site_correlations)
from .stats import (BayesLinearFit, BootstrapResult, DemingFit, OlsFit, bayes_linear_fit,  # noqa: E402
                    deming_fit, group_bootstrap, ols_fit)
from .stats import (LogisticMapFit, OrdinalLogitFit, average_precision, balanced_accuracy, brier,  # noqa: E402
                    calibration_curve, calibration_intercept_slope, f1_macro, logistic_map_fit, ordinal_logit_fit,
                    quadratic_weighted_kappa, recall_per_class, roc_auc)
# reexportada: vive en history porque no necesita numpy
from ..history import save_history_xlsx  # noqa: E402
from .synthetic import SyntheticTruth, synthetic_history  # noqa: E402
from .validation import (Comparison, Fold, FoldFailure, Improvement, OofPredictions, ValidationReport,  # noqa: E402
                         compare_models, dummy_class_fit_predict, dummy_proba_fit_predict, group_kfold,
                         leave_one_group_out, out_of_fold, random_kfold, temporal_split, tramo_groups, validate)

__all__ = ["CORRELATION_RESULT_COLUMNS", "KINDS", "NO_DOMAIN", "STATUSES", "SiteCorrelationFit",
           "SiteCorrelationResult", "fit_site_correlation", "save_site_correlations",
           "BayesLinearFit", "BootstrapResult", "DemingFit", "OlsFit", "bayes_linear_fit", "deming_fit",
           "group_bootstrap", "ols_fit", "LogisticMapFit", "OrdinalLogitFit", "average_precision",
           "balanced_accuracy", "brier", "calibration_curve", "calibration_intercept_slope", "f1_macro",
           "logistic_map_fit", "ordinal_logit_fit", "quadratic_weighted_kappa", "recall_per_class", "roc_auc",
           "SyntheticTruth", "save_history_xlsx", "synthetic_history"]
from .practice import (PRACTICE_RESULT_COLUMNS, Coefficient, Concordance, PracticeAudit,  # noqa: E402
                       PracticeDesign, PracticeTramo, audit_practice, save_practice_results)
__all__ += ["PRACTICE_RESULT_COLUMNS", "Coefficient", "Concordance", "PracticeAudit", "PracticeDesign",
            "PracticeTramo", "audit_practice", "save_practice_results"]
__all__ += ["Comparison", "Fold", "FoldFailure", "Improvement", "OofPredictions", "ValidationReport",
            "compare_models", "dummy_class_fit_predict", "dummy_proba_fit_predict", "group_kfold",
            "leave_one_group_out", "out_of_fold", "random_kfold", "temporal_split", "tramo_groups", "validate"]

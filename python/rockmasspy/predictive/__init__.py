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
from .stats import ExponentialHazardFit, exponential_hazard_map_fit  # noqa: E402
from .stats import FrailtyHazardFit, frailty_hazard_map_fit  # noqa: E402
from .validation import ngi_category  # noqa: E402
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
from .performance import (CALIBRATION_LEVELS, RECOMMENDATION_COLUMNS, IsoprobabilityGrid,  # noqa: E402
                          PerformanceModel, Reason, Recommendation, SupportOption, fit_performance,
                          isoprobability_grid, load_model, recommend, save_model, save_recommendations)
from .performance import poisson_deviance  # noqa: E402
__all__ += ["CALIBRATION_LEVELS", "RECOMMENDATION_COLUMNS", "IsoprobabilityGrid", "PerformanceModel", "Reason",
            "Recommendation", "SupportOption", "fit_performance", "isoprobability_grid", "load_model", "recommend",
            "save_model", "save_recommendations"]
__all__ += ["Comparison", "Fold", "FoldFailure", "Improvement", "OofPredictions", "ValidationReport",
            "compare_models", "dummy_class_fit_predict", "dummy_proba_fit_predict", "group_kfold",
            "leave_one_group_out", "out_of_fold", "random_kfold", "temporal_split", "tramo_groups", "validate"]
__all__ += ["ExponentialHazardFit", "exponential_hazard_map_fit", "ngi_category"]
__all__ += ["FrailtyHazardFit", "frailty_hazard_map_fit", "poisson_deviance"]
from .mine import SCENARIOS, MineScenario, MineTruth, synthetic_mine  # noqa: E402
__all__ += ["SCENARIOS", "MineScenario", "MineTruth", "synthetic_mine"]
from .surrogate import (DOMAIN_BOX_MARGIN, DOMAIN_CHI2_LEVEL, Surrogate, SurrogateData,  # noqa: E402
                        SurrogatePrediction, fit_surrogate, load_runs)
__all__ += ["DOMAIN_BOX_MARGIN", "DOMAIN_CHI2_LEVEL", "Surrogate", "SurrogateData", "SurrogatePrediction",
            "fit_surrogate", "load_runs"]
from .surrogate import USEFUL_RMSE_RATIO, SurrogateValidation, validate_surrogate  # noqa: E402
__all__ += ["USEFUL_RMSE_RATIO", "SurrogateValidation", "validate_surrogate"]
from .surrogate import (OOD_WARN_FRACTION, SurrogatePof, load_points, load_variables,  # noqa: E402
                        surrogate_pof)
__all__ += ["OOD_WARN_FRACTION", "SurrogatePof", "surrogate_pof", "load_points", "load_variables"]

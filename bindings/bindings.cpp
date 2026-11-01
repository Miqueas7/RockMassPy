/**
 * @file bindings.cpp
 * @brief Único punto de exposición del núcleo C++ a Python (módulo rockmasspy._rockmasspy_core).
 */

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/rqd.hpp"

namespace nb = nanobind;
using namespace rockmasspy;

NB_MODULE(_rockmasspy_core, m) {
    m.doc() = "RockMassPy core: rock mass classifications, Hoek-Brown strength and mining geomechanics.";

    nb::enum_<Verification>(m, "Verification", "How well the method's source was verified.")
        .value("Primary", Verification::Primary, "Primary source read")
        .value("PrimaryLaterAuthors", Verification::PrimaryLaterAuthors,
               "Primary source with later-author adjustments")
        .value("Secondary", Verification::Secondary, "Secondary source only");

    nb::class_<MethodInfo>(m, "MethodInfo", "Method id, verification level and source of a result.")
        .def_ro("method_id", &MethodInfo::method_id)
        .def_ro("verification", &MethodInfo::verification)
        .def_ro("source", &MethodInfo::source);

    nb::enum_<JvMethod>(m, "JvMethod", "Jv to RQD correlation edition.")
        .value("Palmstrom1982", JvMethod::Palmstrom1982)
        .value("Palmstrom2005", JvMethod::Palmstrom2005);

    nb::class_<RqdResult>(m, "RqdResult", "RQD in percent with method info and warnings.")
        .def_ro("rqd_pct", &RqdResult::rqd_pct)
        .def_ro("info", &RqdResult::info)
        .def_ro("warnings", &RqdResult::warnings);

    m.def("rqd_from_core", &rqd_from_core, nb::arg("piece_lengths_m"), nb::arg("run_length_m"),
          nb::arg("threshold_m") = 0.10, "RQD from core pieces (pieces >= threshold count).");
    m.def("rqd_priest_hudson", &rqd_priest_hudson, nb::arg("lambda_per_m"), nb::arg("threshold_m") = 0.10,
          "RQD from discontinuity frequency (Priest & Hudson 1976).");
    m.def("rqd_from_jv", &rqd_from_jv, nb::arg("jv"), nb::arg("method") = JvMethod::Palmstrom2005,
          "RQD from volumetric joint count Jv.");
}

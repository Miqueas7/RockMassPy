/**
 * @file bindings.cpp
 * @brief Único punto de exposición del núcleo C++ a Python (módulo rockmasspy._rockmasspy_core).
 */

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>

#include "rockmasspy/method_info.hpp"

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
}

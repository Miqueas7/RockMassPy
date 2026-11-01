/**
 * @file bindings.cpp
 * @brief Único punto de exposición del núcleo C++ a Python (módulo rockmasspy._rockmasspy_core).
 */

#include <nanobind/nanobind.h>
#include <nanobind/stl/optional.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/rmr14.hpp"
#include "rockmasspy/rmr76.hpp"
#include "rockmasspy/rmr89.hpp"
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

    nb::enum_<Water>(m, "Water").value("Dry", Water::Dry).value("Damp", Water::Damp).value("Wet", Water::Wet)
        .value("Dripping", Water::Dripping).value("Flowing", Water::Flowing);
    nb::enum_<OrientationClass>(m, "OrientationClass")
        .value("VeryFavourable", OrientationClass::VeryFavourable).value("Favourable", OrientationClass::Favourable)
        .value("Fair", OrientationClass::Fair).value("Unfavourable", OrientationClass::Unfavourable)
        .value("VeryUnfavourable", OrientationClass::VeryUnfavourable);
    nb::enum_<Application>(m, "Application").value("Tunnel", Application::Tunnel)
        .value("Foundation", Application::Foundation).value("Slope", Application::Slope);
    nb::enum_<StrikeRelation>(m, "StrikeRelation")
        .value("PerpendicularDriveWithDip", StrikeRelation::PerpendicularDriveWithDip)
        .value("PerpendicularDriveAgainstDip", StrikeRelation::PerpendicularDriveAgainstDip)
        .value("Parallel", StrikeRelation::Parallel);
    nb::enum_<Roughness>(m, "Roughness").value("VeryRough", Roughness::VeryRough).value("Rough", Roughness::Rough)
        .value("SlightlyRough", Roughness::SlightlyRough).value("Smooth", Roughness::Smooth)
        .value("Slickensided", Roughness::Slickensided);
    // "None" es palabra reservada de Python: el miembro se expone como None_.
    nb::enum_<Infilling>(m, "Infilling").value("None_", Infilling::None)
        .value("HardUnder5mm", Infilling::HardUnder5mm).value("HardOver5mm", Infilling::HardOver5mm)
        .value("SoftUnder5mm", Infilling::SoftUnder5mm).value("SoftOver5mm", Infilling::SoftOver5mm);
    nb::enum_<Weathering>(m, "Weathering").value("Unweathered", Weathering::Unweathered)
        .value("Slightly", Weathering::Slightly).value("Moderately", Weathering::Moderately)
        .value("Highly", Weathering::Highly).value("Decomposed", Weathering::Decomposed);

    nb::class_<RmrClass>(m, "RmrClass").def_ro("number", &RmrClass::number).def_ro("roman", &RmrClass::roman)
        .def_ro("label", &RmrClass::label);

    nb::class_<JointCondition89>(m, "JointCondition89", "RMR89 joint condition descriptors.")
        .def(nb::init<>())
        .def("__init__",
             [](JointCondition89* self, double persistence_m, double aperture_mm, Roughness roughness,
                Infilling infilling, Weathering weathering) {
                 new (self) JointCondition89{persistence_m, aperture_mm, roughness, infilling, weathering};
             },
             nb::arg("persistence_m"), nb::arg("aperture_mm"), nb::arg("roughness"), nb::arg("infilling"),
             nb::arg("weathering"))
        .def_rw("persistence_m", &JointCondition89::persistence_m)
        .def_rw("aperture_mm", &JointCondition89::aperture_mm)
        .def_rw("roughness", &JointCondition89::roughness)
        .def_rw("infilling", &JointCondition89::infilling)
        .def_rw("weathering", &JointCondition89::weathering);

    nb::class_<Rmr89Input>(m, "Rmr89Input", "RMR89 inputs (exactly one of ucs/is50 and of joint condition forms).")
        .def(nb::init<>())
        .def_rw("ucs_mpa", &Rmr89Input::ucs_mpa)
        .def_rw("is50_mpa", &Rmr89Input::is50_mpa)
        .def_rw("rqd_pct", &Rmr89Input::rqd_pct)
        .def_rw("spacing_m", &Rmr89Input::spacing_m)
        .def_rw("joint_condition", &Rmr89Input::joint_condition)
        .def_rw("joint_condition_rating", &Rmr89Input::joint_condition_rating)
        .def_rw("water", &Rmr89Input::water)
        .def_rw("orientation", &Rmr89Input::orientation)
        .def_rw("application", &Rmr89Input::application);

    nb::class_<Rmr89Result>(m, "Rmr89Result")
        .def_ro("r_strength", &Rmr89Result::r_strength).def_ro("r_rqd", &Rmr89Result::r_rqd)
        .def_ro("r_spacing", &Rmr89Result::r_spacing).def_ro("r_condition", &Rmr89Result::r_condition)
        .def_ro("r_water", &Rmr89Result::r_water).def_ro("basic", &Rmr89Result::basic)
        .def_ro("adjustment", &Rmr89Result::adjustment).def_ro("rmr", &Rmr89Result::rmr)
        .def_ro("rmr_class", &Rmr89Result::rmr_class).def_ro("info", &Rmr89Result::info)
        .def_ro("warnings", &Rmr89Result::warnings);

    m.def("tunnel_orientation_class", &tunnel_orientation_class, nb::arg("rel"), nb::arg("dip_deg"));
    m.def("orientation_adjustment", &orientation_adjustment, nb::arg("c"), nb::arg("app"));
    m.def("rmr_class", &rmr_class, nb::arg("rmr"));
    m.def("jcond89", &jcond89, nb::arg("joint"));
    m.def("rmr89", &rmr89, nb::arg("input"), "RMR89 (Bieniawski 1989) with optional orientation adjustment.");

    nb::enum_<JointCondition76>(m, "JointCondition76")
        .value("VeryRoughTight", JointCondition76::VeryRoughTight)
        .value("SlightlyRoughSlightlyWeathered", JointCondition76::SlightlyRoughSlightlyWeathered)
        .value("SlightlyRoughHighlyWeathered", JointCondition76::SlightlyRoughHighlyWeathered)
        .value("SlickensidedOrThinGouge", JointCondition76::SlickensidedOrThinGouge)
        .value("SoftGougeOrWide", JointCondition76::SoftGougeOrWide);
    nb::enum_<Water76>(m, "Water76").value("CompletelyDry", Water76::CompletelyDry).value("Damp", Water76::Damp)
        .value("ModeratePressure", Water76::ModeratePressure).value("Severe", Water76::Severe);
    nb::class_<Rmr76Input>(m, "Rmr76Input", "RMR76 inputs (exactly one of ucs/is50).")
        .def(nb::init<>())
        .def_rw("ucs_mpa", &Rmr76Input::ucs_mpa).def_rw("is50_mpa", &Rmr76Input::is50_mpa)
        .def_rw("rqd_pct", &Rmr76Input::rqd_pct).def_rw("spacing_m", &Rmr76Input::spacing_m)
        .def_rw("condition", &Rmr76Input::condition).def_rw("water", &Rmr76Input::water)
        .def_rw("orientation", &Rmr76Input::orientation).def_rw("application", &Rmr76Input::application);
    nb::class_<Rmr76Result>(m, "Rmr76Result")
        .def_ro("r_strength", &Rmr76Result::r_strength).def_ro("r_rqd", &Rmr76Result::r_rqd)
        .def_ro("r_spacing", &Rmr76Result::r_spacing).def_ro("r_condition", &Rmr76Result::r_condition)
        .def_ro("r_water", &Rmr76Result::r_water).def_ro("basic", &Rmr76Result::basic)
        .def_ro("adjustment", &Rmr76Result::adjustment).def_ro("rmr", &Rmr76Result::rmr)
        .def_ro("rmr_class", &Rmr76Result::rmr_class).def_ro("info", &Rmr76Result::info)
        .def_ro("warnings", &Rmr76Result::warnings);
    m.def("rating_spacing76", &rating_spacing76, nb::arg("spacing_m"));
    m.def("rmr76", &rmr76, nb::arg("input"), "RMR76 (Bieniawski 1976) with optional orientation adjustment.");

    nb::enum_<Roughness14>(m, "Roughness14").value("VeryRough", Roughness14::VeryRough)
        .value("Rough", Roughness14::Rough).value("Smooth", Roughness14::Smooth)
        .value("Slickensided", Roughness14::Slickensided);
    nb::enum_<Infilling14>(m, "Infilling14").value("HardUnder5mm", Infilling14::HardUnder5mm)
        .value("HardOver5mm", Infilling14::HardOver5mm).value("SoftUnder5mm", Infilling14::SoftUnder5mm)
        .value("SoftOver5mm", Infilling14::SoftOver5mm);
    nb::enum_<Alteration14>(m, "Alteration14").value("Unaltered", Alteration14::Unaltered)
        .value("Moderately", Alteration14::Moderately).value("Highly", Alteration14::Highly)
        .value("Decomposed", Alteration14::Decomposed);
    nb::enum_<Excavation>(m, "Excavation").value("DrillAndBlast", Excavation::DrillAndBlast)
        .value("Tbm", Excavation::Tbm);
    nb::class_<Rmr14Input>(m, "Rmr14Input", "RMR14 inputs (strength and joint-frequency ratings read from the charts).")
        .def(nb::init<>())
        .def_rw("strength_rating", &Rmr14Input::strength_rating)
        .def_rw("joints_per_m_rating", &Rmr14Input::joints_per_m_rating)
        .def_rw("continuity_m", &Rmr14Input::continuity_m).def_rw("roughness", &Rmr14Input::roughness)
        .def_rw("infilling", &Rmr14Input::infilling).def_rw("alteration", &Rmr14Input::alteration)
        .def_rw("water", &Rmr14Input::water).def_rw("id2_pct", &Rmr14Input::id2_pct)
        .def_rw("orientation", &Rmr14Input::orientation).def_rw("excavation", &Rmr14Input::excavation)
        .def_rw("ice", &Rmr14Input::ice);
    nb::class_<Rmr14Result>(m, "Rmr14Result")
        .def_ro("basic", &Rmr14Result::basic).def_ro("f0", &Rmr14Result::f0).def_ro("fe", &Rmr14Result::fe)
        .def_ro("fs", &Rmr14Result::fs).def_ro("rmr", &Rmr14Result::rmr).def_ro("rmr_class", &Rmr14Result::rmr_class)
        .def_ro("info", &Rmr14Result::info).def_ro("warnings", &Rmr14Result::warnings);
    m.def("rating_continuity14", &rating_continuity14, nb::arg("m"));
    m.def("rating_id2_14", &rating_id2_14, nb::arg("id2_pct"));
    m.def("ice_bieniawski_celada", &ice_bieniawski_celada, nb::arg("rmr"), nb::arg("sigma_ci_mpa"), nb::arg("k0"),
          nb::arg("depth_m"), nb::arg("shape_factor_f"), "Elastic behaviour index (Bieniawski & Celada).");
    m.def("fs_face", &fs_face, nb::arg("ice"));
    m.def("rmr14", &rmr14, nb::arg("input"), "RMR14 (Bieniawski 2014), drill-and-blast only.");
}

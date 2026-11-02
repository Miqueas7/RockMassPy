/**
 * @file bindings.cpp
 * @brief Único punto de exposición del núcleo C++ a Python (módulo rockmasspy._rockmasspy_core).
 */

#include <nanobind/nanobind.h>
#include <nanobind/stl/optional.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "rockmasspy/correlations.hpp"
#include "rockmasspy/gsi.hpp"
#include "rockmasspy/hoek_brown.hpp"
#include "rockmasspy/method_info.hpp"
#include "rockmasspy/q_support.hpp"
#include "rockmasspy/mathews.hpp"
#include "rockmasspy/q_system.hpp"
#include "rockmasspy/rmr14.hpp"
#include "rockmasspy/rmr76.hpp"
#include "rockmasspy/rmr89.hpp"
#include "rockmasspy/rqd.hpp"

namespace nb = nanobind;
using namespace rockmasspy;

NB_MODULE(_rockmasspy_core, m) {
    nb::set_leak_warnings(false);  // el aviso de salida tapaba el `error:` de la CLI
    m.doc() = "RockMassPy core: rock mass classifications, Hoek-Brown strength and mining geomechanics.";

    nb::enum_<Verification>(m, "Verification", "How well the method's source was verified.")
        .value("Primary", Verification::Primary,
               "Verified in the original source (or a faithful reproduction of its equations by a cited author)")
        .value("PrimaryLaterAuthors", Verification::PrimaryLaterAuthors,
               "Verified in a later publication by the same authors")
        .value("Secondary", Verification::Secondary, "Secondary source only")
        .value("UserDefined", Verification::UserDefined, "Calibrated by the user on site data");

    nb::class_<MethodInfo>(m, "MethodInfo", "Method id, verification level and source of a result.")
        .def(nb::init<std::string, Verification, std::string>(), nb::arg("method_id"), nb::arg("verification"),
             nb::arg("source"))
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
    m.def("rmr14", &rmr14, nb::arg("input"), "RMR14 per Celada et al. (2014), drill-and-blast only.");

    nb::enum_<QEdition>(m, "QEdition", "Q-system manual edition.")
        .value("NGI2015", QEdition::NGI2015).value("NGI2025", QEdition::NGI2025);
    nb::class_<QInput>(m, "QInput", "Q-system inputs (jn up to 60 covers 3*Jn at intersections).")
        .def(nb::init<>())
        .def(nb::init<double, double, double, double, double, double>(), nb::arg("rqd_pct"), nb::arg("jn"),
             nb::arg("jr"), nb::arg("ja"), nb::arg("jw"), nb::arg("srf"))
        .def_rw("rqd_pct", &QInput::rqd_pct).def_rw("jn", &QInput::jn).def_rw("jr", &QInput::jr)
        .def_rw("ja", &QInput::ja).def_rw("jw", &QInput::jw).def_rw("srf", &QInput::srf);
    nb::class_<QResult>(m, "QResult")
        .def_ro("q", &QResult::q).def_ro("q_base", &QResult::q_base).def_ro("rqd_used", &QResult::rqd_used)
        .def_ro("rock_class", &QResult::rock_class).def_ro("info", &QResult::info)
        .def_ro("warnings", &QResult::warnings);
    m.def("q_value", &q_value, nb::arg("input"), nb::arg("edition") = QEdition::NGI2025,
          "Q and Q' with rock class (NGI 2025 by default).");
    nb::class_<SupportFormulaResult>(m, "SupportFormulaResult", "Classic Q support formula result [V2].")
        .def_ro("value", &SupportFormulaResult::value).def_ro("unit", &SupportFormulaResult::unit)
        .def_ro("info", &SupportFormulaResult::info).def_ro("warnings", &SupportFormulaResult::warnings);
    m.def("max_unsupported_span", &max_unsupported_span, nb::arg("q"), nb::arg("esr"),
          "Maximum unsupported span 2*ESR*Q^0.4 in m (Barton et al. 1980) [V2].");
    m.def("bolt_length_barton1980", &bolt_length_barton1980, nb::arg("span_m"), nb::arg("esr"),
          "Roof bolt length 2 + 0.15*B/ESR in m (Barton et al. 1980) [V2].");
    m.def("roof_pressure_grimstad_barton", &roof_pressure_grimstad_barton, nb::arg("q"), nb::arg("jn"),
          nb::arg("jr"), "Roof support pressure (Grimstad and Barton 1993); unit not stated in the source [V2].");
    nb::class_<FactorResult>(m, "FactorResult", "Mathews stability-graph factor with its source.")
        .def_ro("value", &FactorResult::value).def_ro("info", &FactorResult::info);
    m.def("mathews_factor_a", &mathews_factor_a, nb::arg("ucs_mpa"), nb::arg("induced_stress_mpa"),
          "Mathews factor A (Potvin 1988); 1.0 under relaxation.");
    m.def("mathews_factor_c_gravity", &mathews_factor_c_gravity, nb::arg("surface_inclination_deg"),
          "Mathews factor C for gravity fall and slabbing: 8 - 6 cos(alpha).");
    m.def("mathews_factor_c_sliding", &mathews_factor_c_sliding, nb::arg("joint_dip_deg"),
          "Mathews factor C for sliding on the critical joint.");
    m.def("hydraulic_radius", &hydraulic_radius, nb::arg("area_m2"), nb::arg("perimeter_m"),
          "Hydraulic radius = area / perimeter (m).");
    m.def("hydraulic_radius_rect", &hydraulic_radius_rect, nb::arg("width_m"), nb::arg("length_m"),
          "Hydraulic radius of a rectangular face (m).");
    nb::class_<WallQResult>(m, "WallQResult", "Wall Q with the factor applied (5, 2.5 or 1).")
        .def_ro("q_wall", &WallQResult::q_wall).def_ro("factor", &WallQResult::factor)
        .def_ro("info", &WallQResult::info);
    m.def("wall_q", &wall_q, nb::arg("q"), nb::arg("wall_height_m"), nb::arg("span_m"), nb::arg("high_stress"),
          nb::arg("edition") = QEdition::NGI2025, "Q to use for wall support design.");
    nb::class_<EquivalentDimension>(m, "EquivalentDimension")
        .def_ro("de_m", &EquivalentDimension::de_m).def_ro("esr_used", &EquivalentDimension::esr_used)
        .def_ro("warnings", &EquivalentDimension::warnings).def_ro("info", &EquivalentDimension::info);
    // El caster de char de nanobind da TypeError con "" o "CC": se recibe str para que salga ValueError.
    m.def("equivalent_dimension",
          [](double span_or_height_m, double esr, double q, const std::string& esr_category, QEdition edition) {
              if (esr_category.size() != 1)
                  throw std::invalid_argument(
                      "Domain error [RockMassPy]: parameter 'esr_category' must be one of A-G");
              return equivalent_dimension(span_or_height_m, esr, q, esr_category[0], edition);
          },
          nb::arg("span_or_height_m"), nb::arg("esr"), nb::arg("q"), nb::arg("esr_category"),
          nb::arg("edition") = QEdition::NGI2025,
          "Equivalent dimension De = span or height / ESR (ESR category A-G, any case).");

    nb::class_<GsiResult>(m, "GsiResult")
        .def_ro("gsi", &GsiResult::gsi).def_ro("info", &GsiResult::info).def_ro("warnings", &GsiResult::warnings);
    m.def("gsi_from_jcond89_rqd", &gsi_from_jcond89_rqd, nb::arg("jcond89"), nb::arg("rqd_pct"),
          "Quantified GSI (Hoek, Carter & Diederichs 2013): 1.5*JCond89 + RQD/2.");
    m.def("gsi_from_jcond76_rqd", &gsi_from_jcond76_rqd, nb::arg("jcond76"), nb::arg("rqd_pct"),
          "Quantified GSI (Hoek, Carter & Diederichs 2013): 2*JCond76 + RQD/2.");
    m.def("jcond89_from_jr_ja", &jcond89_from_jr_ja, nb::arg("jr"), nb::arg("ja"));

    nb::enum_<Correlation>(m, "Correlation", "Global correlations between systems (high scatter).")
        .value("RmrFromQ_Bieniawski1976", Correlation::RmrFromQ_Bieniawski1976)
        .value("RmrFromQ_Huang2026", Correlation::RmrFromQ_Huang2026)
        .value("GsiFromQPrime_Hoek1995", Correlation::GsiFromQPrime_Hoek1995)
        .value("GsiFromRmr89Prime_HoekDiederichs2006", Correlation::GsiFromRmr89Prime_HoekDiederichs2006)
        .value("GsiFromRmr76Prime_HoekDiederichs2006", Correlation::GsiFromRmr76Prime_HoekDiederichs2006)
        .value("Rmr14FromRmr89_Osinergmin2017", Correlation::Rmr14FromRmr89_Osinergmin2017)
        .value("Rmr76FromRmr89_Osinergmin2017", Correlation::Rmr76FromRmr89_Osinergmin2017);
    nb::class_<CorrelationResult>(m, "CorrelationResult")
        .def_ro("value", &CorrelationResult::value).def_ro("from_", &CorrelationResult::from)
        .def_ro("to", &CorrelationResult::to).def_ro("info", &CorrelationResult::info)
        .def_ro("warnings", &CorrelationResult::warnings);
    // The result overload goes first so a CorrelationResult is never implicitly converted to a float.
    m.def("correlate", nb::overload_cast<Correlation, const CorrelationResult&>(&correlate), nb::arg("correlation"),
          nb::arg("previous"), "Always raises: correlations must not be chained.");
    m.def("correlate", nb::overload_cast<Correlation, double>(&correlate), nb::arg("correlation"), nb::arg("value"),
          "Global correlation from a measured value.");

    nb::enum_<CorrelationForm>(m, "CorrelationForm", "LogLinear is a*ln(x)+b; Linear is a*x+b.")
        .value("LogLinear", CorrelationForm::LogLinear).value("Linear", CorrelationForm::Linear);
    nb::class_<CustomCorrelation>(m, "CustomCorrelation", "Correlation calibrated by the user on site data.")
        .def(nb::init<>())
        .def("__init__",
             [](CustomCorrelation* self, std::string name, std::string from, std::string to, CorrelationForm form,
                double a, double b, double valid_min, double valid_max, std::string source) {
                 CustomCorrelation c{std::move(name), std::move(from), std::move(to), form, a, b,
                                     valid_min, valid_max, std::move(source)};
                 validate_custom(c);  // valida antes de construir: un dato malo nunca llega a un objeto
                 new (self) CustomCorrelation{std::move(c)};
             },
             nb::arg("name"), nb::arg("from_"), nb::arg("to"), nb::arg("form"), nb::arg("a"), nb::arg("b"),
             nb::arg("valid_min"), nb::arg("valid_max"), nb::arg("source") = "")
        .def_rw("name", &CustomCorrelation::name).def_rw("from_", &CustomCorrelation::from)
        .def_rw("to", &CustomCorrelation::to).def_rw("form", &CustomCorrelation::form)
        .def_rw("a", &CustomCorrelation::a).def_rw("b", &CustomCorrelation::b)
        .def_rw("valid_min", &CustomCorrelation::valid_min).def_rw("valid_max", &CustomCorrelation::valid_max)
        .def_rw("source", &CustomCorrelation::source)
        .def("__eq__", [](const CustomCorrelation& x, const CustomCorrelation& y) { return x == y; });
    m.def("correlate_custom", nb::overload_cast<const CustomCorrelation&, const CorrelationResult&>(&correlate_custom),
          nb::arg("correlation"), nb::arg("previous"), "Always raises: correlations must not be chained.");
    m.def("correlate_custom", nb::overload_cast<const CustomCorrelation&, double>(&correlate_custom),
          nb::arg("correlation"), nb::arg("value"), "Site-calibrated correlation from a measured value.");

    nb::enum_<HbEdition>(m, "HbEdition", "Hoek-Brown criterion edition.")
        .value("HB2002", HbEdition::HB2002).value("HB2018", HbEdition::HB2018);
    nb::enum_<HbApplication>(m, "HbApplication", "Application for the sigma3max limit.")
        .value("Tunnel", HbApplication::Tunnel).value("Slope", HbApplication::Slope);
    nb::class_<HbParams>(m, "HbParams", "Hoek-Brown mb, s, a with method info and warnings.")
        .def_ro("mb", &HbParams::mb).def_ro("s", &HbParams::s).def_ro("a", &HbParams::a)
        .def_ro("info", &HbParams::info).def_ro("warnings", &HbParams::warnings);
    nb::class_<MohrCoulombFit>(m, "MohrCoulombFit", "Equivalent Mohr-Coulomb parameters.")
        .def_ro("phi_deg", &MohrCoulombFit::phi_deg).def_ro("cohesion_mpa", &MohrCoulombFit::cohesion_mpa)
        .def_ro("sigma3max_mpa", &MohrCoulombFit::sigma3max_mpa).def_ro("info", &MohrCoulombFit::info)
        .def_ro("warnings", &MohrCoulombFit::warnings);
    nb::class_<ModulusResult>(m, "ModulusResult", "Rock mass modulus with its unit.")
        .def_ro("value", &ModulusResult::value).def_ro("unit", &ModulusResult::unit)
        .def_ro("info", &ModulusResult::info).def_ro("warnings", &ModulusResult::warnings);
    m.def("hb_params", &hb_params, nb::arg("gsi"), nb::arg("mi"), nb::arg("d"), nb::arg("edition") = HbEdition::HB2018,
          "Hoek-Brown mb, s, a from GSI, mi and D.");
    m.def("hb_sigma1", &hb_sigma1, nb::arg("sigma3_mpa"), nb::arg("sigma_ci_mpa"), nb::arg("params"));
    nb::class_<NormalShear>(m, "NormalShear", "Normal and shear stress (MPa) on the Hoek-Brown envelope.")
        .def_ro("sigma_n_mpa", &NormalShear::sigma_n_mpa).def_ro("tau_mpa", &NormalShear::tau_mpa);
    m.def("hb_normal_shear", &hb_normal_shear, nb::arg("sigma3_mpa"), nb::arg("sigma_ci_mpa"), nb::arg("params"));
    m.def("hb_ucs", &hb_ucs, nb::arg("sigma_ci_mpa"), nb::arg("params"));
    m.def("hb_tensile", &hb_tensile, nb::arg("sigma_ci_mpa"), nb::arg("params"));
    m.def("hb_global_strength", &hb_global_strength, nb::arg("sigma_ci_mpa"), nb::arg("params"));
    m.def("hb_sigma3max", &hb_sigma3max, nb::arg("sigma_cm_mpa"), nb::arg("unit_weight_mn_m3"),
          nb::arg("depth_or_height_m"), nb::arg("application"));
    m.def("hb_mohr_coulomb", &hb_mohr_coulomb, nb::arg("sigma_ci_mpa"), nb::arg("params"), nb::arg("sigma3max_mpa"));
    m.def("em_hoek2002", &em_hoek2002, nb::arg("gsi"), nb::arg("d"), nb::arg("sigma_ci_mpa"));
    m.def("erm_hoek_diederichs_simplified", &erm_hoek_diederichs_simplified, nb::arg("gsi"), nb::arg("d"));
    m.def("erm_hoek_diederichs_generalized", &erm_hoek_diederichs_generalized, nb::arg("gsi"), nb::arg("d"),
          nb::arg("ei_mpa"));
}

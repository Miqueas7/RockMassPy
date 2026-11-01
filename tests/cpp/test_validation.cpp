#include <gtest/gtest.h>

#include <cmath>
#include <stdexcept>
#include <optional>
#include <string>

#include "rockmasspy/validation.hpp"

namespace v = rockmasspy::validation;
TEST(Validation, RejectsNanAndInf) {
    EXPECT_THROW(v::require_finite(std::nan(""), "x"), std::invalid_argument);
    EXPECT_THROW(v::require_finite(INFINITY, "x"), std::invalid_argument);
}
TEST(Validation, Positive) { EXPECT_NO_THROW(v::require_positive(1e-9, "x"));
    EXPECT_THROW(v::require_positive(0.0, "x"), std::invalid_argument); }
TEST(Validation, NonNegative) { EXPECT_NO_THROW(v::require_non_negative(0.0, "x"));
    EXPECT_THROW(v::require_non_negative(-1e-12, "x"), std::invalid_argument); }
TEST(Validation, InRangeIsInclusive) {
    EXPECT_NO_THROW(v::require_in_range(0.0, 0.0, 100.0, "rqd"));
    EXPECT_NO_THROW(v::require_in_range(100.0, 0.0, 100.0, "rqd"));
    EXPECT_THROW(v::require_in_range(100.1, 0.0, 100.0, "rqd"), std::invalid_argument);
}
TEST(Validation, MessageNamesParameter) {
    try { v::require_positive(-1.0, "sigma_ci"); FAIL(); }
    catch (const std::invalid_argument& e) {
        const std::string msg = e.what();
        EXPECT_EQ(msg.rfind("Domain error [RockMassPy]: parameter 'sigma_ci'", 0), 0u);
    }
}
// M1: números con formato corto en el mensaje.
TEST(Validation, MessageNumberFormat) {
    const std::string msg = [] {
        try { v::require_in_range(100.1, 0, 100, "rqd"); } catch (const std::invalid_argument& e) { return std::string(e.what()); }
        return std::string();
    }();
    EXPECT_NE(msg.find("100.1"), std::string::npos) << msg;
    EXPECT_NE(msg.find("[0, 100]"), std::string::npos) << msg;
    try { v::require_positive(-1e-9, "x"); FAIL(); }
    catch (const std::invalid_argument& e) { EXPECT_NE(std::string(e.what()).find("-1e-09"), std::string::npos) << e.what(); }
}
TEST(Validation, RequireSetNamesParameter) {
    try { v::require_set(std::optional<int>{}, "water"); FAIL(); }
    catch (const std::invalid_argument& e) {
        EXPECT_EQ(std::string(e.what()), "Domain error [RockMassPy]: parameter 'water' is required");
    }
    EXPECT_EQ(v::require_set(std::optional<int>{3}, "water"), 3);
}

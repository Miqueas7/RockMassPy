// Mensaje de la std::invalid_argument que lanza f; "" si no lanza.
#pragma once

#include <functional>
#include <stdexcept>
#include <string>

inline std::string error_of(const std::function<void()>& f) {
    try {
        f();
    } catch (const std::invalid_argument& e) {
        return e.what();
    }
    return "";
}

///========================================================
/// @author Gary Yang
/// @brief  Result of a fallible initialize()
/// @copyright (C) Gary 2026
///========================================================




#pragma once


#include <string>
#include <utility>


// Constructors do not perform fallible GPU initialization. Anything that can
// fail gets an initialize() returning one of these, carrying a message that
// names what went wrong.

class InitializationResult {
public:
    static InitializationResult success() { return { true, {} }; }
    static InitializationResult failure(std::string message) {
        return { false, std::move(message) };
    }

    // explicit: `if (result)` works, `bool ok = result` does not compile.
    explicit operator bool() const { return m_succeeded; }
    const char* message() const { return m_message.c_str(); }

private:
    InitializationResult(bool succeeded, std::string message)
        : m_succeeded(succeeded), m_message(std::move(message)) {}

    bool        m_succeeded = false;
    std::string m_message;
};

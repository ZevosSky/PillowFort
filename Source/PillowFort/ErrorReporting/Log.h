///========================================================
/// @author Gary Yang
/// @brief  Simple Logging for myself 
/// @copyright (C) Gary 2026
///========================================================




#pragma once


// Macro for debug logging

#ifdef _DEBUG
#define LOG_INFO(message) Log::info(message)
#define LOG_WARNING(message) Log::warning(message)
#define LOG_ERROR(message) Log::error(message)

#else
#define LOG_INFO(message) (void(0))
#define LOG_WARNING(message) (void(0))
#define LOG_ERROR(message) (void(0))

#endif




class Log {
public:
    static void info(const char* message);
    static void warning(const char* message);
    static void error(const char* message);
};
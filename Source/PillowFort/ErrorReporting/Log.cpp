


#include "Log.h"
#include <iostream>


// Might have to change this if I add multithreading 

void Log::info(const char* message) {
    std::cout << "[INFO] " << message << std::endl;
}

void Log::warning(const char* message) {
    std::cout << "[WARNING] " << message << std::endl;
}

void Log::error(const char* message) {
    std::cerr << "[ERROR] " << message << std::endl;
}
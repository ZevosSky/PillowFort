///==========================================================================
/// \file Camera.h
/// \brief Basic camera functionality assumes coordinate system 
///        with right-handed convention based on Garry Herron's cam modded
/// \author Gary Herron
/// \author Gary Yang
/// \copyright Copyright (c) 2026 Gary Herron
///==========================================================================


#pragma once

// GLM's switches (GLM_ENABLE_EXPERIMENTAL for gtx/transform below) are set once
// in premake5.lua for every file. Defining one here would give files that
// include this header a different GLM from files that do not.

#include <glm/glm.hpp>
#include <glm/gtx/transform.hpp>




class Camera
{
 public:
    bool modified;  
    float ry;           
    float front;
    float back;

    float spin;
    float tilt;
    glm::vec3 eye;
    float rate;

    float startSpin;
    float startTilt;
    glm::vec3 startEye;
    float startTime;
    float endTime;    

    bool lmb=false;
    bool mmb=false;
    bool rmb=false; 
    bool shift=false;
    bool ctrl=false;
    bool alt=false;

    float posx = 0.0;
    float posy = 0.0;
    
    Camera();

    void reset(glm::vec3 eye=glm::vec3(0,0,0), float rate=1.0,
               float spin=0.0, float tilt=0.0,
               float ry=0.57, float front=0.1, float back=1000.0);
    
    void animateTo(float deltaTime, float spin, float tilt, const glm::vec3& eye);
    glm::mat4 perspective(const float aspect);
    glm::mat4 view(float time);

    void mouseMove(const float x, const float y);
    void eyeMoveBy(const glm::vec3& step);
    void setMousePosition(const float x, const float y);
    void wheel(const int dir);
    void viewParms();

};
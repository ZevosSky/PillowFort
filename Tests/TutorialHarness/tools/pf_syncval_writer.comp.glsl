// Positive-control shader: writes binding 1 (a storage buffer) through a descriptor.
#version 450
layout(local_size_x = 64) in;
layout(set = 0, binding = 0) readonly buffer Input  { uint values[]; } inputBuffer;
layout(set = 0, binding = 1) writeonly buffer Output { uint values[]; } outputBuffer;
void main()
{
    outputBuffer.values[gl_GlobalInvocationID.x] = gl_GlobalInvocationID.x;
}

/*
 * @author   Tutorial harness
 * @brief    Ask an X11 window to close the way a window manager would: a
 *           WM_PROTOCOLS / WM_DELETE_WINDOW client message. GLFW turns that into
 *           glfwWindowShouldClose, so the program runs its real shutdown path.
 *           (Xvfb has no window manager, and xdotool's windowclose destroys the
 *           window instead of asking.)
 * @copyright 2026 Gary Yang
 *
 * Usage: pf_xclose <window id, decimal or 0x hex>
 */
#include <X11/Xlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char** argv)
{
    if (argc != 2) { fprintf(stderr, "usage: pf_xclose <window-id>\n"); return 2; }
    Display* display = XOpenDisplay(NULL);
    if (!display) { fprintf(stderr, "pf_xclose: cannot open display\n"); return 1; }

    const Window window = (Window)strtoul(argv[1], NULL, 0);
    XEvent event;
    memset(&event, 0, sizeof(event));
    event.xclient.type         = ClientMessage;
    event.xclient.window       = window;
    event.xclient.message_type = XInternAtom(display, "WM_PROTOCOLS", False);
    event.xclient.format       = 32;
    event.xclient.data.l[0]    = (long)XInternAtom(display, "WM_DELETE_WINDOW", False);
    event.xclient.data.l[1]    = CurrentTime;

    const Status sent = XSendEvent(display, window, False, NoEventMask, &event);
    XFlush(display);
    XCloseDisplay(display);
    return sent ? 0 : 1;
}

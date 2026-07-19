#include "ui.h"

#define K_ENTER 28
#define K_BACK  14
#define K_UP    103
#define K_DOWN  108

void nui_init(struct nui_state *s, int app_count) {
    s->screen = NUI_HOME;
    s->selected = 0;
    s->app_count = app_count;
    s->launch_request = -1;
}

void nui_key(struct nui_state *s, int code) {
    if (s->screen == NUI_HOME) {
        if (code == K_ENTER) {
            s->screen = NUI_MENU;
            s->selected = 0;
        }
        return;
    }

    if (s->app_count <= 0) {
        if (code == K_ENTER || code == K_BACK) s->screen = NUI_HOME;
        return;
    }

    if (code == K_DOWN) {
        s->selected = (s->selected + 1) % s->app_count;
    } else if (code == K_UP) {
        s->selected = (s->selected - 1 + s->app_count) % s->app_count;
    } else if (code == K_ENTER) {
        s->launch_request = s->selected;
    } else if (code == K_BACK) {
        s->screen = NUI_HOME;
    }
}

int nui_take_launch(struct nui_state *s) {
    int r = s->launch_request;
    s->launch_request = -1;
    return r;
}

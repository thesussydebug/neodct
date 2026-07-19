#ifndef NUI_H
#define NUI_H

enum nui_screen { NUI_HOME = 0, NUI_MENU = 1 };

struct nui_state {
    int screen;
    int selected;
    int app_count;
    int launch_request;
};

void nui_init(struct nui_state *s, int app_count);

void nui_key(struct nui_state *s, int code);

int nui_take_launch(struct nui_state *s);

#endif

#ifndef NLAY_H
#define NLAY_H

#define NLAY_MAX_ELEMENTS 32
#define NLAY_MAX_LEVELS   8
#define NLAY_PATH_MAX     160
#define NLAY_TEXT_MAX     64

enum nlay_type { NLAY_UNKNOWN = 0, NLAY_TEXT = 1, NLAY_ICON_SET = 2 };

struct nlay_element {
    int type;
    int x, y;

    char text[NLAY_TEXT_MAX];
    int font_size;
    char anchor[16];
    char color[16];

    int count;
    char prefix[8];
    int sim_val;
    char custom_images[NLAY_MAX_LEVELS][NLAY_PATH_MAX];
};

struct nlay_layout {
    char background[NLAY_PATH_MAX];
    struct nlay_element elements[NLAY_MAX_ELEMENTS];
    int count;
};

int nlay_parse(const char *json, struct nlay_layout *out);

#endif

#include "layout.h"

#include <stdlib.h>
#include <string.h>

struct cur { const char *p; };

static void skip_ws(struct cur *c) {
    while (*c->p == ' ' || *c->p == '\t' || *c->p == '\n' || *c->p == '\r') c->p++;
}

static int accept(struct cur *c, char ch) {
    skip_ws(c);
    if (*c->p == ch) { c->p++; return 1; }
    return 0;
}

static int parse_string(struct cur *c, char *out, size_t cap) {
    skip_ws(c);
    if (*c->p != '"') return -1;
    c->p++;
    size_t n = 0;
    while (*c->p && *c->p != '"') {
        char ch = *c->p++;
        if (ch == '\\' && *c->p) ch = *c->p++;
        if (out && n + 1 < cap) out[n++] = ch;
    }
    if (*c->p != '"') return -1;
    c->p++;
    if (out) out[n] = 0;
    return 0;
}

static int parse_number(struct cur *c, int *out) {
    skip_ws(c);
    char *end;
    double v = strtod(c->p, &end);
    if (end == c->p) return -1;
    c->p = end;
    if (out) *out = (int)v;
    return 0;
}

static int skip_value(struct cur *c);

static int skip_container(struct cur *c, char open, char close) {
    if (!accept(c, open)) return -1;
    int depth = 1;
    while (depth > 0) {
        skip_ws(c);
        if (!*c->p) return -1;
        if (*c->p == '"') { if (parse_string(c, NULL, 0) != 0) return -1; continue; }
        if (*c->p == open) depth++;
        else if (*c->p == close) depth--;
        c->p++;
    }
    return 0;
}

static int skip_value(struct cur *c) {
    skip_ws(c);
    if (*c->p == '"') return parse_string(c, NULL, 0);
    if (*c->p == '{') return skip_container(c, '{', '}');
    if (*c->p == '[') return skip_container(c, '[', ']');
    if (strncmp(c->p, "null", 4) == 0) { c->p += 4; return 0; }
    if (strncmp(c->p, "true", 4) == 0) { c->p += 4; return 0; }
    if (strncmp(c->p, "false", 5) == 0) { c->p += 5; return 0; }
    return parse_number(c, NULL);
}

static int parse_custom_images(struct cur *c, struct nlay_element *e) {
    if (!accept(c, '{')) return -1;
    skip_ws(c);
    if (accept(c, '}')) return 0;
    for (;;) {
        char key[16];
        if (parse_string(c, key, sizeof key) != 0) return -1;
        if (!accept(c, ':')) return -1;
        int level = atoi(key);
        if (level >= 0 && level < NLAY_MAX_LEVELS)
            { if (parse_string(c, e->custom_images[level], NLAY_PATH_MAX) != 0) return -1; }
        else if (skip_value(c) != 0) return -1;
        if (accept(c, ',')) continue;
        if (accept(c, '}')) return 0;
        return -1;
    }
}

static int parse_element(struct cur *c, struct nlay_element *e) {
    memset(e, 0, sizeof *e);
    if (!accept(c, '{')) return -1;
    skip_ws(c);
    if (accept(c, '}')) return 0;
    for (;;) {
        char key[32];
        if (parse_string(c, key, sizeof key) != 0) return -1;
        if (!accept(c, ':')) return -1;

        int rc = 0;
        if (strcmp(key, "type") == 0) {
            char t[24];
            rc = parse_string(c, t, sizeof t);
            if (rc == 0)
                e->type = strcmp(t, "text") == 0 ? NLAY_TEXT
                        : strcmp(t, "icon_set") == 0 ? NLAY_ICON_SET
                        : NLAY_UNKNOWN;
        }
        else if (strcmp(key, "x") == 0) rc = parse_number(c, &e->x);
        else if (strcmp(key, "y") == 0) rc = parse_number(c, &e->y);
        else if (strcmp(key, "font_size") == 0) rc = parse_number(c, &e->font_size);
        else if (strcmp(key, "count") == 0) rc = parse_number(c, &e->count);
        else if (strcmp(key, "sim_val") == 0) rc = parse_number(c, &e->sim_val);
        else if (strcmp(key, "text") == 0) rc = parse_string(c, e->text, NLAY_TEXT_MAX);
        else if (strcmp(key, "anchor") == 0) rc = parse_string(c, e->anchor, sizeof e->anchor);
        else if (strcmp(key, "color") == 0) rc = parse_string(c, e->color, sizeof e->color);
        else if (strcmp(key, "prefix") == 0) rc = parse_string(c, e->prefix, sizeof e->prefix);
        else if (strcmp(key, "custom_images") == 0) rc = parse_custom_images(c, e);
        else rc = skip_value(c);
        if (rc != 0) return -1;

        if (accept(c, ',')) continue;
        if (accept(c, '}')) return 0;
        return -1;
    }
}

static int parse_elements(struct cur *c, struct nlay_layout *out) {
    if (!accept(c, '[')) return -1;
    skip_ws(c);
    if (accept(c, ']')) return 0;
    for (;;) {
        struct nlay_element e;
        if (parse_element(c, &e) != 0) return -1;
        if (e.type != NLAY_UNKNOWN && out->count < NLAY_MAX_ELEMENTS)
            out->elements[out->count++] = e;
        if (accept(c, ',')) continue;
        if (accept(c, ']')) return 0;
        return -1;
    }
}

int nlay_parse(const char *json, struct nlay_layout *out) {
    struct cur c = { json };
    memset(out, 0, sizeof *out);
    if (!accept(&c, '{')) return -1;
    skip_ws(&c);
    if (accept(&c, '}')) return 0;
    for (;;) {
        char key[32];
        if (parse_string(&c, key, sizeof key) != 0) return -1;
        if (!accept(&c, ':')) return -1;

        int rc;
        if (strcmp(key, "background") == 0) {
            skip_ws(&c);
            if (*c.p == '"') rc = parse_string(&c, out->background, NLAY_PATH_MAX);
            else rc = skip_value(&c);
        }
        else if (strcmp(key, "elements") == 0) rc = parse_elements(&c, out);
        else rc = skip_value(&c);
        if (rc != 0) return -1;

        if (accept(&c, ',')) continue;
        if (accept(&c, '}')) return 0;
        return -1;
    }
}

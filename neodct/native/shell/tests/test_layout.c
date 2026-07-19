#include "../layout.h"
#include "../../neopix/tests/runner.h"

#include <stdlib.h>

static const struct nlay_element *find_by_text(const struct nlay_layout *l,
                                               const char *text) {
    for (int i = 0; i < l->count; i++)
        if (strcmp(l->elements[i].text, text) == 0) return &l->elements[i];
    return NULL;
}

static const struct nlay_element *find_by_prefix(const struct nlay_layout *l,
                                                 const char *prefix) {
    for (int i = 0; i < l->count; i++)
        if (strcmp(l->elements[i].prefix, prefix) == 0) return &l->elements[i];
    return NULL;
}

static char *real_layout(void) {
    long n;
    unsigned char *raw = load_fix("ui_home.json", &n);
    char *s = malloc(n + 1);
    memcpy(s, raw, n);
    s[n] = 0;
    free(raw);
    return s;
}

static void test_parses_real_layout_element_count(void) {
    char *json = real_layout();
    struct nlay_layout l;
    int rc = nlay_parse(json, &l);
    CHECK("parses shipping ui_home.json", rc == 0 && l.count == 4);
    free(json);
}

static void test_parses_text_element_fields(void) {
    char *json = real_layout();
    struct nlay_layout l;
    nlay_parse(json, &l);
    const struct nlay_element *e = find_by_text(&l, "No Service");
    CHECK("text element fields parsed",
          e && e->type == NLAY_TEXT && e->x == 120 && e->y == 71 &&
          e->font_size == 12 && strcmp(e->anchor, "center_h") == 0 &&
          strcmp(e->color, "white") == 0);
    free(json);
}

static void test_parses_icon_set_fields(void) {
    char *json = real_layout();
    struct nlay_layout l;
    nlay_parse(json, &l);
    const struct nlay_element *e = find_by_prefix(&l, "bat");
    CHECK("icon_set fields parsed",
          e && e->type == NLAY_ICON_SET && e->count == 5 &&
          e->x == 210 && e->y == 24 && e->sim_val == 4);
    free(json);
}

static void test_parses_custom_images_map(void) {
    char *json = real_layout();
    struct nlay_layout l;
    nlay_parse(json, &l);
    const struct nlay_element *e = find_by_prefix(&l, "bat");
    CHECK("custom_images map parsed by level",
          e && strcmp(e->custom_images[0],
                      "/NeoDCT/System/ui/resources/img/battery/bat-0.png") == 0 &&
          strcmp(e->custom_images[4],
                 "/NeoDCT/System/ui/resources/img/battery/bat-4.png") == 0);
    free(json);
}

static void test_null_background_is_empty(void) {
    struct nlay_layout l;
    nlay_parse("{\"background\": null, \"elements\": []}", &l);
    CHECK("null background yields empty string", l.background[0] == 0);
}

static void test_string_background_parsed(void) {
    struct nlay_layout l;
    nlay_parse("{\"background\": \"/a/b.png\", \"elements\": []}", &l);
    CHECK("string background parsed", strcmp(l.background, "/a/b.png") == 0);
}

static void test_tolerates_whitespace_and_negatives(void) {
    struct nlay_layout l;
    const char *j =
        "{\n \"background\" : null ,\n \"elements\" : [\n"
        "  { \"type\" : \"text\" , \"text\" : \"Hi\" , \"x\" : -5 , \"y\" : 7 }\n ]\n}";
    int rc = nlay_parse(j, &l);
    CHECK("whitespace and negative numbers handled",
          rc == 0 && l.count == 1 && l.elements[0].x == -5 && l.elements[0].y == 7);
}

static void test_rejects_malformed_json(void) {
    struct nlay_layout l;
    CHECK("malformed json rejected", nlay_parse("{\"elements\": [", &l) != 0);
}

static void test_unknown_type_is_skipped_not_fatal(void) {
    struct nlay_layout l;
    const char *j = "{\"elements\": ["
                    "{\"type\":\"future_widget\",\"x\":1,\"y\":2},"
                    "{\"type\":\"text\",\"text\":\"ok\",\"x\":3,\"y\":4}]}";
    int rc = nlay_parse(j, &l);
    CHECK("unknown element type skipped, parse continues",
          rc == 0 && l.count == 1 && strcmp(l.elements[0].text, "ok") == 0);
}

int main(void) {
    test_parses_real_layout_element_count();
    test_parses_text_element_fields();
    test_parses_icon_set_fields();
    test_parses_custom_images_map();
    test_null_background_is_empty();
    test_string_background_parsed();
    test_tolerates_whitespace_and_negatives();
    test_rejects_malformed_json();
    test_unknown_type_is_skipped_not_fatal();
    return SUMMARY();
}

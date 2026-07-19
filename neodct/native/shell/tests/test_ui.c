#include "../ui.h"
#include "../../neopix/tests/runner.h"

#define K_ENTER 28
#define K_BACK  14
#define K_UP    103
#define K_DOWN  108

static struct nui_state menu_at(int app_count) {
    struct nui_state s;
    nui_init(&s, app_count);
    nui_key(&s, K_ENTER);
    return s;
}

static void test_starts_on_home(void) {
    struct nui_state s;
    nui_init(&s, 5);
    CHECK("starts on home screen", s.screen == NUI_HOME);
}

static void test_enter_on_home_opens_menu_at_first_app(void) {
    struct nui_state s = menu_at(5);
    CHECK("enter on home opens menu at index 0",
          s.screen == NUI_MENU && s.selected == 0);
}

static void test_down_advances_selection(void) {
    struct nui_state s = menu_at(5);
    nui_key(&s, K_DOWN);
    CHECK("down advances selection", s.selected == 1);
}

static void test_down_wraps_at_end(void) {
    struct nui_state s = menu_at(3);
    nui_key(&s, K_DOWN);
    nui_key(&s, K_DOWN);
    nui_key(&s, K_DOWN);
    CHECK("down wraps to first", s.selected == 0);
}

static void test_up_wraps_to_last(void) {
    struct nui_state s = menu_at(3);
    nui_key(&s, K_UP);
    CHECK("up from first wraps to last", s.selected == 2);
}

static void test_back_returns_to_home(void) {
    struct nui_state s = menu_at(5);
    nui_key(&s, K_DOWN);
    nui_key(&s, K_BACK);
    CHECK("back returns to home", s.screen == NUI_HOME);
}

static void test_enter_in_menu_requests_launch(void) {
    struct nui_state s = menu_at(5);
    nui_key(&s, K_DOWN);
    nui_key(&s, K_DOWN);
    nui_key(&s, K_ENTER);
    CHECK("enter requests launch of selected app", s.launch_request == 2);
}

static void test_launch_request_clears_after_read(void) {
    struct nui_state s = menu_at(5);
    nui_key(&s, K_ENTER);
    int first = nui_take_launch(&s);
    int second = nui_take_launch(&s);
    CHECK("launch request is one-shot", first == 0 && second == -1);
}

static void test_empty_app_list_never_launches(void) {
    struct nui_state s;
    nui_init(&s, 0);
    nui_key(&s, K_ENTER);
    nui_key(&s, K_DOWN);
    nui_key(&s, K_ENTER);
    CHECK("empty app list cannot launch", s.launch_request == -1);
}

static void test_empty_app_list_back_exits_menu(void) {
    struct nui_state s;
    nui_init(&s, 0);
    nui_key(&s, K_ENTER);
    nui_key(&s, K_BACK);
    CHECK("empty app list still backs out", s.screen == NUI_HOME);
}

int main(void) {
    test_starts_on_home();
    test_enter_on_home_opens_menu_at_first_app();
    test_down_advances_selection();
    test_down_wraps_at_end();
    test_up_wraps_to_last();
    test_back_returns_to_home();
    test_enter_in_menu_requests_launch();
    test_launch_request_clears_after_read();
    test_empty_app_list_never_launches();
    test_empty_app_list_back_exits_menu();
    return SUMMARY();
}

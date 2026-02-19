from System.ui.framework import SoftKeyBar, MessageDialog

def run(ui):
    screen_w = getattr(ui, "W", 300)
    content_bottom = getattr(ui, "content_bottom", getattr(ui, "H", 172) - getattr(ui, "SOFTKEY_H", 30))

    # Clear screen
    ui.draw.rectangle((0, 0, screen_w, content_bottom), fill="black")
    softkey = SoftKeyBar(ui)
    softkey.update("Testing123")
    warningmsg = MessageDialog(ui, "This is a test of the error screen")

    # Draw Hello World centered
    text = "Hello World"
    w, h = ui.get_text_size(text, ui.font_xl)
    ui.draw.text(
        ((screen_w - w) // 2, (content_bottom - h) // 2),
        text,
        font=ui.font_xl,
        fill="white"
    )

    ui.fb.update(ui.canvas)

    while True:
        warningmsg.show()
        # Wait for a key
        key = ui.wait_for_key()
        # BACK / MENU / ENTER exits app
        if key in (46, 28, 50):
            return

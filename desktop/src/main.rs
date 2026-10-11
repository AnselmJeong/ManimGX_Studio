use gpui_kit::{
    component::{Theme, ThemeMode, TitleBar},
    *,
};
use manimgx_studio::studio::{
    ExportFilm, NewFilm, OpenProject, Quit, RenderFilm, SaveProject, Studio, TogglePlayback,
};

fn main() {
    application().with_assets(assets::Assets).run(|cx| {
        init(cx);
        Theme::change(ThemeMode::Dark, None, cx);
        cx.bind_keys([
            KeyBinding::new("secondary-enter", RenderFilm, Some("Studio")),
            KeyBinding::new("secondary-n", NewFilm, Some("Studio")),
            KeyBinding::new("secondary-s", SaveProject, Some("Studio")),
            KeyBinding::new("secondary-o", OpenProject, Some("Studio")),
            KeyBinding::new("secondary-e", ExportFilm, Some("Studio")),
            KeyBinding::new("secondary-p", TogglePlayback, Some("Studio")),
            KeyBinding::new("secondary-q", Quit, None),
        ]);
        cx.on_action(|_: &Quit, cx| cx.quit());
        cx.set_menus(vec![
            Menu {
                name: "ManimGX Studio".into(),
                items: vec![MenuItem::action("종료", Quit)],
                disabled: false,
            },
            Menu {
                name: "파일".into(),
                items: vec![
                    MenuItem::action("새 영상", NewFilm),
                    MenuItem::action("프로젝트 열기…", OpenProject),
                    MenuItem::action("프로젝트 저장…", SaveProject),
                    MenuItem::action("MP4 내보내기…", ExportFilm),
                ],
                disabled: false,
            },
            Menu {
                name: "영상".into(),
                items: vec![
                    MenuItem::action("영상 만들기", RenderFilm),
                    MenuItem::action("미리보기 재생 / 일시 정지", TogglePlayback),
                ],
                disabled: false,
            },
        ]);
        // Initial and minimum bounds are platform window geometry, in physical pixels.
        let options = WindowOptions {
            window_bounds: Some(WindowBounds::Windowed(Bounds::centered(
                None,
                size(px(1440.0), px(900.0)),
                cx,
            ))),
            window_min_size: Some(size(px(1080.0), px(720.0))),
            app_id: Some("ai.academa.manimgx-studio".into()),
            ..TitleBar::window_options()
        };
        let (_, studio) = open_window(options, cx, |window, cx| {
            window.set_window_title("ManimGX Studio");
            cx.new(|cx| Studio::new(window, cx))
        })
        .expect("ManimGX Studio 창을 열 수 없습니다");
        let studio = studio.downgrade();
        cx.on_app_quit(move |cx| {
            let _ = studio.update(cx, |studio, _| studio.prepare_to_quit());
            let executor = cx.background_executor().clone();
            async move {
                executor.timer(std::time::Duration::from_millis(250)).await;
            }
        })
        .detach();
        cx.on_window_closed(|cx, _| {
            if cx.windows().is_empty() {
                cx.quit();
            }
        })
        .detach();
        cx.activate(true);
    });
}

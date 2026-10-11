mod authoring;
use authoring::Authoring;
use std::{
    path::{Path, PathBuf},
    time::{Duration, Instant},
};

use gpui_kit::{
    component::{
        ActiveTheme, Disableable, IconName, Selectable, Sizable, Theme, ThemeMode, TitleBar,
        button::{Button, ButtonVariants},
        h_flex,
        input::{Editor, EditorState, Input, InputEvent, InputState},
        resizable::{h_resizable, resizable_panel},
        slider::{Slider, SliderEvent, SliderState},
        tab::{Tab, TabBar},
        v_flex,
    },
    prelude::*,
    *,
};

use crate::{
    catalog::{LESSONS, lesson},
    project::{Project, Session, data_directory},
    render_job::{Preview, Quality, RenderEvent, RenderJob, Runtime},
};

actions!(
    studio,
    [
        RenderFilm,
        NewFilm,
        GenerateFilm,
        SaveProject,
        OpenProject,
        ExportFilm,
        TogglePlayback,
        Quit
    ]
);

pub struct Studio {
    session: Session,
    ai: Authoring,
    directory: PathBuf,
    editor: Entity<EditorState>,
    title: Entity<InputState>,
    scene: Entity<InputState>,
    parameter: Entity<SliderState>,
    pace: Entity<SliderState>,
    position: Entity<SliderState>,
    focus: FocusHandle,
    previews: Vec<Option<Preview>>,
    preview_cache: Entity<RetainAllImageCache>,
    paths: Vec<Option<PathBuf>>,
    job: Option<RenderJob>,
    quality: Quality,
    inspector_tab: usize,
    status: String,
    error: Option<String>,
    changed: Option<Instant>,
    seconds: f64,
    playing: bool,
    last_tick: Instant,
    last_elapsed: u64,
    _subscriptions: Vec<Subscription>,
    _ticker: Task<()>,
    smoke_result: Option<PathBuf>,
}

impl Studio {
    pub fn new(window: &mut Window, cx: &mut Context<Self>) -> Self {
        let directory = data_directory();
        if std::env::args().any(|argument| argument == "--smoke-test") {
            let mut studio = Self::with_directory(
                directory
                    .join("native-smoke")
                    .join(crate::project::new_id()),
                window,
                cx,
            );
            studio.inspector_tab = 1;
            studio.smoke_result = Some(directory.join("native-smoke-result.json"));
            cx.defer_in(window, |this, window, cx| {
                this.render_film(&RenderFilm, window, cx)
            });
            studio
        } else {
            Self::with_directory(directory, window, cx)
        }
    }

    pub fn prepare_to_quit(&mut self) {
        if self.changed.is_some() {
            let _ = self.session.save(&self.directory);
        }
        if let Some(job) = &self.ai.job {
            job.cancel();
        }
        if let Some(job) = &self.job {
            job.cancel();
        }
    }

    fn with_directory(directory: PathBuf, window: &mut Window, cx: &mut Context<Self>) -> Self {
        let (session, error) = match Session::load(&directory) {
            Ok(session) => (session, None),
            Err(error) => (
                Session::default(),
                Some(format!(
                    "자동 저장을 복구하지 못했습니다. 원본 session.json을 확인해 주세요.\n{error}"
                )),
            ),
        };
        let project = &session.projects[session.selected];
        let editor = cx.new(|cx| {
            EditorState::new(window, cx)
                .language("python")
                .line_number(true)
                .default_value(project.source.clone())
        });
        let title = cx.new(|cx| InputState::new(window, cx).default_value(project.title.clone()));
        let scene = cx.new(|cx| InputState::new(window, cx).default_value(project.scene.clone()));
        let parameter = cx.new(|_| {
            SliderState::new()
                .min(0.0)
                .max(100.0)
                .step(1.0)
                .default_value(50.0)
        });
        let pace = cx.new(|_| {
            SliderState::new()
                .min(0.6)
                .max(1.6)
                .step(0.1)
                .default_value(project.parameter("PACE").unwrap_or(1.0))
        });
        let position = cx.new(|_| {
            SliderState::new()
                .min(0.0)
                .max(100.0)
                .step(0.1)
                .default_value(0.0)
        });
        let ai = Authoring::new(&project.prompt_draft, window, cx);
        let subscriptions = vec![
            cx.subscribe(&ai.prompt, |this, state, event, cx| {
                if matches!(
                    event,
                    InputEvent::PressEnter {
                        secondary: true,
                        shift: false
                    }
                ) {
                    this.start_ai("create", cx);
                }
                if matches!(event, InputEvent::Change) {
                    let value = state.read(cx).value().to_string();
                    if this.current().prompt_draft != value {
                        this.current_mut().prompt_draft = value;
                        this.mark_changed(cx);
                    }
                }
            }),
            cx.subscribe_in(&editor, window, |this, editor, event, window, cx| {
                if matches!(event, InputEvent::Change) {
                    let source = editor.read(cx).value().to_string();
                    if this.current().source != source {
                        this.current_mut().source = source;
                        this.mark_changed(cx);
                        this.sync_sliders(window, cx);
                    }
                }
            }),
            cx.subscribe(&title, |this, state, event, cx| {
                if matches!(event, InputEvent::Change) {
                    let title = state.read(cx).value().to_string();
                    if this.current().title != title {
                        this.current_mut().title = title;
                        this.mark_changed(cx);
                    }
                }
            }),
            cx.subscribe(&scene, |this, state, event, cx| {
                if matches!(event, InputEvent::Change) {
                    let scene = state.read(cx).value().to_string();
                    if this.current().scene != scene {
                        this.current_mut().scene = scene;
                        this.mark_changed(cx);
                    }
                }
            }),
            cx.subscribe_in(&parameter, window, |this, _, event, window, cx| {
                if let SliderEvent::Change(value) = event {
                    let (min, max, step) = lesson(&this.current().lesson_id).range;
                    let value = ((min + (max - min) * value.start() / 100.0) / step).round() * step;
                    this.apply_parameter("VALUE", value, window, cx);
                }
                cx.notify();
            }),
            cx.subscribe_in(&pace, window, |this, _, event, window, cx| {
                if let SliderEvent::Change(value) = event {
                    this.apply_parameter("PACE", value.start(), window, cx);
                }
                cx.notify();
            }),
            cx.subscribe(&position, |this, _, event, cx| {
                if let SliderEvent::Change(value) = event {
                    if let Some(preview) = this.preview() {
                        this.seconds = preview.duration * f64::from(value.start()) / 100.0;
                    }
                    this.playing = false;
                    cx.notify();
                }
            }),
        ];
        let ticker = cx.spawn_in(window, async move |this, cx| {
            loop {
                cx.background_executor()
                    .timer(Duration::from_millis(83))
                    .await;
                if this
                    .update_in(cx, |this, window, cx| this.tick(window, cx))
                    .is_err()
                {
                    break;
                }
            }
        });
        let count = session.projects.len();
        let previews: Vec<_> = session
            .projects
            .iter()
            .map(|project| Preview::restore(project, &directory))
            .collect();
        let seconds = previews[session.selected]
            .as_ref()
            .map_or(0.0, |preview| preview.duration * 0.55);
        position.update(cx, |state, cx| {
            state.set_value(if seconds > 0.0 { 55.0 } else { 0.0 }, window, cx)
        });
        let studio = Self {
            session,
            ai,
            directory,
            editor,
            title,
            scene,
            parameter,
            pace,
            position,
            focus: cx.focus_handle(),
            previews,
            preview_cache: RetainAllImageCache::new(cx),
            paths: vec![None; count],
            job: None,
            quality: Quality::Draft,
            inspector_tab: 0,
            status: "새 영상을 누르고 만들고 싶은 내용을 입력해 보세요".into(),
            error,
            changed: None,
            seconds,
            playing: false,
            last_tick: Instant::now(),
            last_elapsed: 0,
            _subscriptions: subscriptions,
            _ticker: ticker,
            smoke_result: None,
        };
        studio.sync_sliders(window, cx);
        studio.focus.focus(window, cx);
        studio
    }

    fn current(&self) -> &Project {
        &self.session.projects[self.session.selected]
    }
    fn current_mut(&mut self) -> &mut Project {
        &mut self.session.projects[self.session.selected]
    }
    fn preview(&self) -> Option<&Preview> {
        self.previews[self.session.selected].as_ref()
    }
    fn is_stale(&self) -> bool {
        self.preview().is_some_and(|preview| {
            preview.source != self.current().source || preview.scene != self.current().scene
        })
    }

    fn mark_changed(&mut self, cx: &mut Context<Self>) {
        self.changed = Some(Instant::now());
        cx.notify();
    }

    fn sync_sliders(&self, window: &mut Window, cx: &mut Context<Self>) {
        let lesson = lesson(&self.current().lesson_id);
        let value = self.current().parameter("VALUE").unwrap_or(lesson.initial);
        let fraction = ((value - lesson.range.0) / (lesson.range.1 - lesson.range.0) * 100.0)
            .clamp(0.0, 100.0);
        self.parameter
            .update(cx, |state, cx| state.set_value(fraction, window, cx));
        self.pace.update(cx, |state, cx| {
            state.set_value(
                self.current()
                    .parameter("PACE")
                    .unwrap_or(1.0)
                    .clamp(0.6, 1.6),
                window,
                cx,
            )
        });
    }

    fn apply_parameter(
        &mut self,
        name: &str,
        value: f32,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        if self.current_mut().set_parameter(name, value) {
            let source = self.current().source.clone();
            self.editor
                .update(cx, |state, cx| state.set_value(source, window, cx));
            self.mark_changed(cx);
        }
    }

    fn sync_editor(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let project = self.current().clone();
        self.ai.plan.clear();
        self.ai.summary.clear();
        self.ai.prompt.update(cx, |state, cx| {
            state.set_value(project.prompt_draft.clone(), window, cx)
        });
        self.editor
            .update(cx, |state, cx| state.set_value(project.source, window, cx));
        self.title
            .update(cx, |state, cx| state.set_value(project.title, window, cx));
        self.scene
            .update(cx, |state, cx| state.set_value(project.scene, window, cx));
        self.sync_sliders(window, cx);
        self.seconds = 0.0;
        self.playing = false;
        self.preview_cache
            .update(cx, |cache, cx| cache.clear(window, cx));
        self.position
            .update(cx, |state, cx| state.set_value(0.0, window, cx));
    }

    fn select(&mut self, ix: usize, window: &mut Window, cx: &mut Context<Self>) {
        if self.busy() || ix == self.session.selected {
            return;
        }
        self.session.selected = ix;
        self.error = None;
        self.sync_editor(window, cx);
        self.mark_changed(cx);
    }

    fn tick(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.poll_ai(window, cx);
        let now = Instant::now();
        let delta = now.duration_since(self.last_tick).as_secs_f64();
        self.last_tick = now;
        if self.playing
            && let Some(preview) = self.preview()
        {
            let duration = preview.duration;
            self.seconds = (self.seconds + delta).min(duration);
            if self.seconds >= duration {
                self.playing = false;
            }
            self.position.update(cx, |state, cx| {
                state.set_value((self.seconds / duration * 100.0) as f32, window, cx)
            });
            cx.notify();
        }
        let events: Vec<_> = self
            .job
            .as_ref()
            .map(|job| job.events.try_iter().collect())
            .unwrap_or_default();
        for event in events {
            match event {
                RenderEvent::Phase(phase) => self.status = phase,
                RenderEvent::Cancelled => {
                    self.job = None;
                    self.status = "렌더링을 중단했습니다. 수정한 코드는 보관됩니다.".into();
                }
                RenderEvent::Finished(result) => {
                    self.job = None;
                    match result {
                        Ok(preview) => {
                            if let Some(path) = &self.smoke_result {
                                let result = serde_json::json!({"success": true, "video": preview.movie(), "width": preview.width, "height": preview.height, "duration": preview.duration, "frames": preview.frames.len()});
                                let _ = crate::project::atomic_write(
                                    path,
                                    result.to_string().as_bytes(),
                                );
                            }
                            self.current_mut().last_render = preview
                                .directory
                                .file_name()
                                .map(|name| name.to_string_lossy().into_owned());
                            self.mark_changed(cx);
                            self.preview_cache
                                .update(cx, |cache, cx| cache.clear(window, cx));
                            self.status = format!(
                                "렌더링 완료 · {} × {} · {:.1}초",
                                preview.width, preview.height, preview.duration
                            );
                            // Begin at a representative frame, with explicit play required.
                            self.seconds = (preview.duration * 0.55).min(preview.duration);
                            self.position
                                .update(cx, |state, cx| state.set_value(55.0, window, cx));
                            self.previews[self.session.selected] = Some(preview);
                        }
                        Err(error) => {
                            if let Some(path) = &self.smoke_result {
                                let result = serde_json::json!({"success": false, "error": format!("{error:#}")});
                                let _ = crate::project::atomic_write(
                                    path,
                                    result.to_string().as_bytes(),
                                );
                            }
                            self.status = "렌더링 실패 · 오류 내용을 확인해 주세요".into();
                            self.error = Some(format!("{error:#}"));
                        }
                    }
                }
            }
            cx.notify();
        }
        if let Some(started) = self
            .job
            .as_ref()
            .map(|job| job.started)
            .or_else(|| self.ai.job.as_ref().map(|job| job.started))
        {
            let elapsed = started.elapsed().as_secs();
            if elapsed != self.last_elapsed {
                self.last_elapsed = elapsed;
                cx.notify();
            }
        }
        if self
            .changed
            .is_some_and(|changed| changed.elapsed() > Duration::from_millis(650))
        {
            self.changed = None;
            if let Err(error) = self.session.save(&self.directory) {
                self.error = Some(format!("자동 저장에 실패했습니다: {error}"));
            }
            cx.notify();
        }
    }

    fn render_film(&mut self, _: &RenderFilm, _: &mut Window, cx: &mut Context<Self>) {
        if self.inspector_tab == 0 {
            self.start_ai("create", cx);
            return;
        }
        if self.busy() {
            return;
        }
        self.playing = false;
        self.error = None;
        let result = Runtime::discover().and_then(|runtime| {
            RenderJob::start(
                runtime,
                self.current().clone(),
                self.quality,
                &self.directory,
            )
        });
        match result {
            Ok(job) => {
                self.job = Some(job);
                self.status = "렌더러 시작 중".into();
                self.last_elapsed = 0;
            }
            Err(error) => {
                self.error = Some(format!("{error:#}"));
                self.status = "렌더링을 시작하지 못했습니다".into();
            }
        }
        cx.notify();
    }

    fn toggle_playback(&mut self, _: &TogglePlayback, _: &mut Window, cx: &mut Context<Self>) {
        if let Some(preview) = self.preview() {
            if self.seconds >= preview.duration {
                self.seconds = 0.0;
            }
            self.playing = !self.playing;
            self.last_tick = Instant::now();
            cx.notify();
        }
    }

    fn save_project(&mut self, _: &SaveProject, _: &mut Window, cx: &mut Context<Self>) {
        let project = self.current().clone();
        if let Some(path) = self.paths[self.session.selected].clone() {
            match project.save(&path) {
                Ok(()) => self.status = format!("프로젝트 저장됨 · {}", path.display()),
                Err(error) => self.error = Some(error.to_string()),
            }
            cx.notify();
            return;
        }
        let selected = self.session.selected;
        let suggested = format!("{}.mgx", safe_filename(&project.title));
        let receiver = cx.prompt_for_new_path(
            &user_directory("Documents", &self.directory),
            Some(&suggested),
        );
        cx.spawn(async move |this, cx| match receiver.await {
            Ok(Ok(Some(path))) => {
                let result = project.save(&path);
                let _ = this.update(cx, |this, cx| {
                    match result {
                        Ok(()) => {
                            this.paths[selected] = Some(path.clone());
                            this.status = format!("프로젝트 저장됨 · {}", path.display());
                        }
                        Err(error) => this.error = Some(error.to_string()),
                    }
                    cx.notify();
                });
            }
            Ok(Err(error)) => {
                let _ = this.update(cx, |this, cx| {
                    this.error = Some(error.to_string());
                    cx.notify();
                });
            }
            _ => {}
        })
        .detach();
    }

    fn open_project(&mut self, _: &OpenProject, window: &mut Window, cx: &mut Context<Self>) {
        if self.busy() {
            return;
        }
        let receiver = cx.prompt_for_paths(PathPromptOptions {
            files: true,
            directories: false,
            multiple: false,
            prompt: Some("ManimGX 프로젝트 (.mgx) 열기".into()),
        });
        cx.spawn_in(window, async move |this, cx| match receiver.await {
            Ok(Ok(Some(paths))) => {
                if let Some(path) = paths.first() {
                    let result = Project::load(path);
                    let _ = this.update_in(cx, |this, window, cx| {
                        match result {
                            Ok(mut project) => {
                                project.id = crate::project::new_id();
                                if this.busy() {
                                    return;
                                }
                                this.session.projects.push(project);
                                this.previews.push(None);
                                this.paths.push(Some(path.clone()));
                                this.session.selected = this.session.projects.len() - 1;
                                this.sync_editor(window, cx);
                                this.mark_changed(cx);
                                this.status = "프로젝트를 열었습니다".into();
                                this.error = None;
                            }
                            Err(error) => {
                                this.error = Some(format!("프로젝트를 열지 못했습니다: {error:#}"))
                            }
                        }
                        cx.notify();
                    });
                }
            }
            Ok(Err(error)) => {
                let _ = this.update(cx, |this, cx| {
                    this.error = Some(error.to_string());
                    cx.notify();
                });
            }
            _ => {}
        })
        .detach();
    }

    fn export_film(&mut self, _: &ExportFilm, _: &mut Window, cx: &mut Context<Self>) {
        let Some(preview) = self.preview().cloned().filter(|_| !self.is_stale()) else {
            return;
        };
        let suggested = format!("{}.mp4", safe_filename(&self.current().title));
        let receiver =
            cx.prompt_for_new_path(&user_directory("Movies", &self.directory), Some(&suggested));
        cx.spawn(async move |this, cx| match receiver.await {
            Ok(Ok(Some(path))) => {
                let destination = path.clone();
                let result = cx
                    .background_spawn(async move { preview.export(&destination) })
                    .await;
                let _ = this.update(cx, |this, cx| {
                    match result {
                        Ok(_) => {
                            this.status = format!("MP4 내보내기 완료 · {}", path.display());
                            cx.reveal_path(&path);
                        }
                        Err(error) => {
                            this.error = Some(format!("영상을 저장하지 못했습니다: {error}"))
                        }
                    }
                    cx.notify();
                });
            }
            Ok(Err(error)) => {
                let _ = this.update(cx, |this, cx| {
                    this.error = Some(error.to_string());
                    cx.notify();
                });
            }
            _ => {}
        })
        .detach();
    }

    fn render_sidebar(&self, cx: &mut Context<Self>) -> impl IntoElement {
        v_flex()
            .size_full()
            .bg(cx.theme().sidebar)
            .border_r_1()
            .border_color(cx.theme().border)
            .child(
                v_flex()
                    .p_4()
                    .gap_1()
                    .child(
                        div()
                            .text_lg()
                            .font_weight(FontWeight::SEMIBOLD)
                            .child("ManimGX Studio"),
                    )
                    .child(
                        div()
                            .text_xs()
                            .text_color(cx.theme().muted_foreground)
                            .child("개념을 움직이는 그림으로"),
                    ),
            )
            .child(
                div().px_3().child(
                    Button::new("new-film")
                        .label("새 영상")
                        .w_full()
                        .disabled(self.busy())
                        .on_click(
                            cx.listener(|this, _, window, cx| this.new_film(&NewFilm, window, cx)),
                        ),
                ),
            )
            .child(
                div()
                    .px_4()
                    .pt_4()
                    .pb_2()
                    .text_xs()
                    .text_color(cx.theme().muted_foreground)
                    .child("프로젝트"),
            )
            .child(
                v_flex()
                    .id("lesson-list")
                    .flex_1()
                    .min_h_0()
                    .overflow_y_scroll()
                    .px_2()
                    .gap_1()
                    .children(
                        self.session
                            .projects
                            .iter()
                            .enumerate()
                            .map(|(ix, project)| {
                                let selected = self.session.selected == ix;
                                v_flex()
                                    .gap_1()
                                    .pb_2()
                                    .child(
                                        Button::new(SharedString::from(format!(
                                            "project-{}",
                                            project.id
                                        )))
                                        .ghost()
                                        .w_full()
                                        .label(project.title.clone())
                                        .selected(selected)
                                        .disabled(self.busy())
                                        .on_click(
                                            cx.listener(move |this, _, window, cx| {
                                                this.select(ix, window, cx)
                                            }),
                                        ),
                                    )
                                    .child(
                                        div()
                                            .px_3()
                                            .text_xs()
                                            .text_color(cx.theme().muted_foreground)
                                            .child(
                                                if project.lesson_id != "custom"
                                                    && ix < LESSONS.len()
                                                {
                                                    lesson(&project.lesson_id).category
                                                } else {
                                                    "내 프로젝트"
                                                },
                                            ),
                                    )
                            }),
                    ),
            )
            .child(
                v_flex()
                    .p_3()
                    .gap_2()
                    .border_t_1()
                    .border_color(cx.theme().border)
                    .child(
                        Button::new("open-project")
                            .ghost()
                            .label("프로젝트 열기…")
                            .icon(IconName::FolderOpen)
                            .disabled(self.busy())
                            .on_click(cx.listener(|this, _, window, cx| {
                                this.open_project(&OpenProject, window, cx)
                            })),
                    )
                    .child(
                        Button::new("documentation")
                            .ghost()
                            .label("ManimGX 사용 안내")
                            .icon(IconName::BookOpen)
                            .on_click(|_, _, cx| cx.open_url("https://manimgx.academa.ai/")),
                    ),
            )
    }

    fn render_preview(&self, cx: &mut Context<Self>) -> impl IntoElement {
        let lesson = lesson(&self.current().lesson_id);
        let preview = self.preview();
        let custom = self.current().lesson_id == "custom";
        let plan = if self.ai.plan.is_empty() {
            &self.current().plan
        } else {
            &self.ai.plan
        };
        let steps: Vec<(String, String)> = if plan.is_empty() && !custom {
            lesson
                .steps
                .iter()
                .map(|(a, b)| (a.to_string(), b.to_string()))
                .collect()
        } else {
            plan.iter()
                .map(|scene| {
                    (
                        format!("{} · {:.0}초", scene.title, scene.seconds),
                        scene.description.clone(),
                    )
                })
                .collect()
        };
        let image_path = preview
            .map(|preview| preview.frame_path(self.seconds))
            .unwrap_or_else(|| {
                asset_path(&format!(
                    "{}.jpg",
                    if custom { "new-film" } else { lesson.id }
                ))
            });
        let duration = preview.map_or(0.0, |preview| preview.duration);
        v_flex()
            .size_full()
            .min_w_0()
            .min_h_0()
            .child(
                v_flex()
                    .px_5()
                    .pt_5()
                    .pb_4()
                    .gap_2()
                    .child(
                        div()
                            .text_xs()
                            .text_color(cx.theme().muted_foreground)
                            .child(if custom { "내 영상" } else { lesson.category }),
                    )
                    .child(
                        div()
                            .text_2xl()
                            .font_weight(FontWeight::SEMIBOLD)
                            .child(self.current().title.clone()),
                    )
                    .child(
                        div()
                            .text_sm()
                            .text_color(cx.theme().muted_foreground)
                            .child(if custom { if self.current().summary.is_empty() { "만들고 싶은 내용을 오른쪽에 입력하세요".to_owned() } else { self.current().summary.clone() } } else { lesson.question.to_owned() }),
                    ),
            )
            .child(
                v_flex()
                    .id("preview-scroll")
                    .flex_1()
                    .min_h_0()
                    .overflow_y_scroll()
                    .child(
                        v_flex()
                            .px_5()
                            .gap_4()
                            .pb_5()
                            .child(
                                v_flex()
                                    .gap_2()
                                    .child(
                                        div()
                                            .w_full()
                                            .aspect_ratio(16.0 / 9.0)
                                            .bg(cx.theme().muted)
                                            .rounded(cx.theme().radius)
                                            .overflow_hidden()
                                            .child(
                                                img(image_path)
                                                    .image_cache(&self.preview_cache)
                                                    .id("film-preview")
                                                    .size_full()
                                                    .object_fit(ObjectFit::Contain)
                                                    .with_fallback(move || {
                                                        v_flex()
                                                            .size_full()
                                                            .items_center()
                                                            .justify_center()
                                                            .gap_4()
                                                            .child(
                                                                div()
                                                                    .text_2xl()
                                                                    .child(if custom { "새로운 이야기를 영상으로" } else { lesson.formula }),
                                                            )
                                                            .child(if custom { "AI 제작에 주제와 원하는 설명을 적어주세요" } else { "영상 만들기를 눌러 시작하세요" })
                                                            .into_any_element()
                                                    }),
                                            ),
                                    )
                                    .child(
                                        h_flex()
                                            .justify_between()
                                            .gap_2()
                                            .text_xs()
                                            .text_color(cx.theme().muted_foreground)
                                            .child(if preview.is_none() && custom {
                                                "생성한 영상이 여기에 표시됩니다"
                                            } else if preview.is_none() {
                                                "예제 스틸 · 내 영상을 렌더링해 보세요"
                                            } else if self.is_stale() {
                                                "이전 렌더 · 변경한 코드를 반영하려면 다시 만드세요"
                                            } else {
                                                "영상 미리보기 · 최대 12 fps · 무음"
                                            })
                                            .child(if let Some(preview) = preview {
                                                format!(
                                                    "{} × {} · {:.1} fps",
                                                    preview.width, preview.height, preview.fps
                                                )
                                            } else {
                                                "16:9".into()
                                            }),
                                    ),
                            )
                            .child(
                                h_flex()
                                    .gap_3()
                                    .child(
                                        Button::new("play")
                                            .ghost()
                                            .icon(if self.playing {
                                                IconName::Pause
                                            } else {
                                                IconName::Play
                                            })
                                            .label(if self.playing {
                                                "일시 정지"
                                            } else {
                                                "재생"
                                            })
                                            .disabled(preview.is_none())
                                            .small()
                                            .on_click(cx.listener(|this, _, window, cx| {
                                                this.toggle_playback(&TogglePlayback, window, cx)
                                            })),
                                    )
                                    .child(div().flex_1().min_w_0().child(
                                        Slider::new(&self.position).disabled(preview.is_none()),
                                    ))
                                    .child(
                                        div()
                                            .text_xs()
                                            .text_color(cx.theme().muted_foreground)
                                            .child(format!(
                                                "{} / {}",
                                                time_label(self.seconds),
                                                time_label(duration)
                                            )),
                                    ),
                            )
                            .child(
                                h_flex()
                                    .gap_2()
                                    .child(
                                        Button::new("open-movie")
                                            .label("영상 플레이어로 열기")
                                            .ghost()
                                            .small()
                                            .disabled(preview.is_none())
                                            .on_click(cx.listener(|this, _, _, cx| {
                                                if let Some(preview) = this.preview() {
                                                    cx.open_with_system(&preview.movie());
                                                }
                                            })),
                                    )
                                    .child(
                                        Button::new("export-film")
                                            .label("MP4 내보내기…")
                                            .small()
                                            .disabled(
                                                preview.is_none()
                                                    || self.is_stale()
                                                    || self.busy(),
                                            )
                                            .on_click(cx.listener(|this, _, window, cx| {
                                                this.export_film(&ExportFilm, window, cx)
                                            })),
                                    ),
                            )
                            .child(
                                v_flex()
                                    .pt_3()
                                    .gap_3()
                                    .border_t_1()
                                    .border_color(cx.theme().border)
                                    .child(
                                        div()
                                            .font_weight(FontWeight::SEMIBOLD)
                                            .text_sm()
                                            .child("설명 흐름"),
                                    )
                                    .children(steps.iter().enumerate().map(
                                        |(ix, (title, explanation))| {
                                            h_flex()
                                                .items_start()
                                                .gap_3()
                                                .child(
                                                    div()
                                                        .w_6()
                                                        .text_sm()
                                                        .text_color(cx.theme().muted_foreground)
                                                        .child(format!("{:02}", ix + 1)),
                                                )
                                                .child(
                                                    v_flex()
                                                        .flex_1()
                                                        .gap_1()
                                                        .child(
                                                            div()
                                                                .text_sm()
                                                                .font_weight(FontWeight::MEDIUM)
                                                                .child(title.clone()),
                                                        )
                                                        .child(
                                                            div()
                                                                .text_sm()
                                                                .text_color(
                                                                    cx.theme().muted_foreground,
                                                                )
                                                                .child(explanation.clone()),
                                                        ),
                                                )
                                        },
                                    )),
                            )
                            .when_some(self.error.as_ref(), |view, error| {
                                view.child(
                                    v_flex()
                                        .p_4()
                                        .gap_2()
                                        .bg(cx.theme().muted)
                                        .rounded(cx.theme().radius)
                                        .child(
                                            h_flex()
                                                .justify_between()
                                                .child(
                                                    div()
                                                        .text_color(cx.theme().danger)
                                                        .text_sm()
                                                        .child("작업을 완료하지 못했습니다"),
                                                )
                                                .child(
                                                    Button::new("dismiss-error")
                                                        .ghost()
                                                        .small()
                                                        .label("닫기")
                                                        .on_click(cx.listener(|this, _, _, cx| {
                                                            this.error = None;
                                                            cx.notify();
                                                        })),
                                                ),
                                        )
                                        .child(div().text_xs().child(error.clone())),
                                )
                            }),
                    ),
            )
    }

    fn render_settings(&self, cx: &mut Context<Self>) -> AnyElement {
        if self.current().lesson_id == "custom" {
            return v_flex().p_4().gap_4()
                .child(label("프로젝트 이름", cx)).child(Input::new(&self.title).id("project-title").disabled(self.busy()))
                .child(label("영상 품질", cx))
                .child(h_flex().gap_2().children([Quality::Draft, Quality::Full].into_iter().map(|quality| {
                    Button::new(if quality == Quality::Draft { "quality-draft" } else { "quality-full" }).small().label(quality.label()).selected(self.quality == quality).disabled(self.busy())
                        .on_click(cx.listener(move |this, _, _, cx| { this.quality = quality; cx.notify(); }))
                })))
                .child(div().text_sm().child("내용·장면 길이·색상은 AI 제작에서 대화로 수정하세요. 이 설정은 다음 영상 생성에 적용됩니다."))
                .into_any_element();
        }
        let lesson = lesson(&self.current().lesson_id);
        let (min, max, step) = lesson.range;
        let value = ((min + (max - min) * self.parameter.read(cx).value().start() / 100.0) / step)
            .round()
            * step;
        v_flex().id("settings-scroll").flex_1().min_h_0().overflow_y_scroll()
            .child(v_flex().p_4().gap_5()
                .child(v_flex().gap_2().child(label("프로젝트 이름", cx)).child(Input::new(&self.title).id("project-title").disabled(self.busy())))
                .child(v_flex().gap_2().child(label("이 영상에서 배울 것", cx))
                    .child(div().text_sm().line_height(relative(1.6)).child(lesson.summary)))
                .child(v_flex().gap_3().pt_4().border_t_1().border_color(cx.theme().border)
                    .child(label("직접 바꿔 보기", cx))
                    .child(h_flex().justify_between().gap_2().text_sm().child(lesson.parameter)
                        .child(div().font_weight(FontWeight::SEMIBOLD).child(format!("{value:.1} {}", lesson.unit))))
                    .child(Slider::new(&self.parameter).disabled(self.busy() || self.current().parameter("VALUE").is_none()))
                    .child(h_flex().justify_between().text_xs().text_color(cx.theme().muted_foreground).child(format!("{min:.1}")).child(format!("{max:.1}")))
                    .child(div().text_xs().text_color(cx.theme().muted_foreground).child(if self.current().parameter("VALUE").is_some() { "수치를 바꾼 뒤 다시 렌더링하면 변화가 보입니다." } else { "코드에서 VALUE를 직접 계산하고 있습니다." })))
                .child(v_flex().gap_3()
                    .child(h_flex().justify_between().text_sm().child("설명 시간 배율").child(format!("{:.1}×", self.pace.read(cx).value().start())))
                    .child(Slider::new(&self.pace).disabled(self.busy() || self.current().parameter("PACE").is_none()))
                    .child(div().text_xs().text_color(cx.theme().muted_foreground).child("값이 클수록 천천히 설명합니다. 물리 시간도 같은 비율로 느려집니다.")))
                .child(v_flex().gap_3().pt_4().border_t_1().border_color(cx.theme().border)
                    .child(label("영상 품질", cx))
                    .child(h_flex().gap_2().children([Quality::Draft, Quality::Full].into_iter().map(|quality| {
                        Button::new(if quality == Quality::Draft { "quality-draft" } else { "quality-full" }).small()
                            .label(quality.label()).selected(self.quality == quality).disabled(self.busy())
                            .on_click(cx.listener(move |this, _, _, cx| { this.quality = quality; cx.notify(); }))
                    })))
                    .child(div().text_xs().text_color(cx.theme().muted_foreground).child("MP4 · H.264 · 30 fps · 16:9")))
                .child(v_flex().gap_2().pt_4().border_t_1().border_color(cx.theme().border)
                    .child(label("핵심 관계", cx))
                    .child(div().text_lg().child(lesson.formula)))
                .child(Button::new("duplicate-template").ghost().label("원본 예제로 새로 시작").small().disabled(self.busy())
                    .on_click(cx.listener(|this, _, window, cx| {
                        let project = Project::from_lesson(crate::catalog::lesson(&this.current().lesson_id));
                        this.session.projects.push(project); this.previews.push(None); this.paths.push(None);
                        this.session.selected = this.session.projects.len() - 1;
                        this.sync_editor(window, cx); this.mark_changed(cx);
                    })))).into_any_element()
    }

    fn render_inspector(&self, cx: &mut Context<Self>) -> impl IntoElement {
        v_flex()
            .size_full()
            .min_h_0()
            .min_w_0()
            .bg(cx.theme().sidebar)
            .border_l_1()
            .border_color(cx.theme().border)
            .child(
                TabBar::new("inspector-tabs")
                    .selected_index(self.inspector_tab)
                    .child(Tab::new().label("AI 제작"))
                    .child(Tab::new().label("영상 설정"))
                    .child(Tab::new().label("Python 코드"))
                    .on_click(cx.listener(|this, ix, _, cx| {
                        this.inspector_tab = *ix;
                        cx.notify();
                    })),
            )
            .child(if self.inspector_tab == 0 {
                self.render_authoring(cx).into_any_element()
            } else if self.inspector_tab == 1 {
                self.render_settings(cx).into_any_element()
            } else {
                v_flex()
                    .flex_1()
                    .min_h_0()
                    .min_w_0()
                    .gap_3()
                    .child(
                        v_flex()
                            .px_4()
                            .pt_3()
                            .gap_2()
                            .child(label("장면 클래스", cx))
                            .child(Input::new(&self.scene).disabled(self.busy())),
                    )
                    .child(
                        div().flex_1().min_h_0().min_w_0().child(
                            Editor::new(&self.editor)
                                .readonly(self.busy())
                                .h_full()
                                .bordered(false)
                                .aria_label("ManimGX Python 코드"),
                        ),
                    )
                    .child(
                        div()
                            .px_4()
                            .pb_3()
                            .text_xs()
                            .text_color(cx.theme().muted_foreground)
                            .child("이 Mac에서 실행되는 Python 코드입니다. ⌘↵ 렌더링 · ⌘S 저장"),
                    )
                    .into_any_element()
            })
            .when(self.inspector_tab != 0, |view| {
                view.child(
                    v_flex()
                        .p_4()
                        .gap_2()
                        .border_t_1()
                        .border_color(cx.theme().border)
                        .child(if self.job.is_some() {
                            Button::new("cancel-render")
                                .label("렌더링 중단")
                                .w_full()
                                .on_click(cx.listener(|this, _, _, cx| {
                                    if let Some(job) = &this.job {
                                        job.cancel();
                                        this.status = "렌더러 중단 중".into();
                                    }
                                    cx.notify();
                                }))
                                .into_any_element()
                        } else {
                            Button::new("render-film")
                                .label("영상 만들기")
                                .icon(IconName::Play)
                                .primary()
                                .w_full()
                                .tooltip("⌘Enter")
                                .on_click(cx.listener(|this, _, window, cx| {
                                    this.render_film(&RenderFilm, window, cx)
                                }))
                                .into_any_element()
                        })
                        .child(
                            div()
                                .text_xs()
                                .text_center()
                                .text_color(cx.theme().muted_foreground)
                                .child("설정을 바꾸고 영상을 다시 렌더링합니다"),
                        ),
                )
            })
    }
}

impl Render for Studio {
    fn render(&mut self, window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        let rem = window.rem_size();
        let sidebar_width = self
            .session
            .pane_widths
            .first()
            .copied()
            .filter(|v| v.is_finite())
            .unwrap_or(14.0)
            .clamp(11.5, 20.0);
        let inspector_width = self
            .session
            .pane_widths
            .get(2)
            .copied()
            .filter(|v| v.is_finite())
            .unwrap_or(25.0)
            .clamp(20.5, 40.0);
        let render_status = if let Some(started) = self
            .job
            .as_ref()
            .map(|job| job.started)
            .or_else(|| self.ai.job.as_ref().map(|job| job.started))
        {
            format!("{} · {}초 경과", self.status, started.elapsed().as_secs())
        } else {
            self.status.clone()
        };
        v_flex()
            .size_full()
            .bg(cx.theme().background)
            .text_color(cx.theme().foreground)
            .text_sm()
            .key_context("Studio")
            .track_focus(&self.focus)
            .on_action(cx.listener(Self::render_film))
            .on_action(cx.listener(Self::new_film))
            .on_action(cx.listener(Self::generate_film))
            .on_action(cx.listener(Self::save_project))
            .on_action(cx.listener(Self::open_project))
            .on_action(cx.listener(Self::export_film))
            .on_action(cx.listener(Self::toggle_playback))
            .child(
                TitleBar::new().child(
                    h_flex()
                        .w_full()
                        .justify_between()
                        .pr_2()
                        .child(
                            div()
                                .text_sm()
                                .text_color(cx.theme().muted_foreground)
                                .child("ManimGX Studio  /  개념 영상 작업실"),
                        )
                        .child(
                            h_flex()
                                .gap_2()
                                .child(
                                    Button::new("theme")
                                        .ghost()
                                        .xsmall()
                                        .label(if cx.theme().is_dark() {
                                            "라이트 모드"
                                        } else {
                                            "다크 모드"
                                        })
                                        .on_click(|_, window, cx| {
                                            Theme::change(
                                                if cx.theme().is_dark() {
                                                    ThemeMode::Light
                                                } else {
                                                    ThemeMode::Dark
                                                },
                                                Some(window),
                                                cx,
                                            );
                                        }),
                                )
                                .child(
                                    Button::new("save-project")
                                        .ghost()
                                        .xsmall()
                                        .label("프로젝트 저장…")
                                        .tooltip("⌘S")
                                        .on_click(cx.listener(|this, _, window, cx| {
                                            this.save_project(&SaveProject, window, cx)
                                        })),
                                ),
                        ),
                ),
            )
            .child(
                div().flex_1().min_h_0().min_w_0().child(
                    h_resizable("studio-panes")
                        .on_resize(cx.listener(
                            |this,
                             state: &Entity<gpui_kit::component::resizable::ResizableState>,
                             window,
                             cx| {
                                this.session.pane_widths = state
                                    .read(cx)
                                    .sizes()
                                    .iter()
                                    .map(|width| *width / window.rem_size())
                                    .collect();
                                this.mark_changed(cx);
                            },
                        ))
                        // Resizable takes Pixels: resolve the app's rem-based pane geometry at the boundary.
                        .child(
                            resizable_panel()
                                .size(rem * sidebar_width)
                                .size_range(rem * 11.5..rem * 20.0)
                                .child(self.render_sidebar(cx)),
                        )
                        .child(
                            resizable_panel()
                                .size_range(rem * 27.0..rem * 100.0)
                                .child(self.render_preview(cx)),
                        )
                        .child(
                            resizable_panel()
                                .size(rem * inspector_width)
                                .size_range(rem * 20.5..rem * 55.0)
                                .child(self.render_inspector(cx)),
                        ),
                ),
            )
            .child(
                h_flex()
                    .h_8()
                    .px_4()
                    .gap_3()
                    .border_t_1()
                    .border_color(cx.theme().border)
                    .text_xs()
                    .child(
                        div()
                            .id("render-status")
                            .role(Role::Status)
                            .aria_label(render_status.clone())
                            .flex_1()
                            .min_w_0()
                            .truncate()
                            .text_color(cx.theme().muted_foreground)
                            .child(render_status),
                    )
                    .child(div().text_color(cx.theme().muted_foreground).child(
                        if self.changed.is_some() {
                            "저장 중"
                        } else {
                            "작업 자동 보관"
                        },
                    )),
            )
    }
}

impl Drop for Studio {
    fn drop(&mut self) {
        if self.changed.is_some() {
            let _ = self.session.save(&self.directory);
        }
        if let Some(job) = &self.ai.job {
            job.cancel();
        }
        if let Some(job) = &self.job {
            job.cancel();
        }
    }
}

fn label(text: &'static str, cx: &App) -> impl IntoElement {
    div()
        .text_xs()
        .font_weight(FontWeight::MEDIUM)
        .text_color(cx.theme().muted_foreground)
        .child(text)
}

fn time_label(seconds: f64) -> String {
    format!("{:02}:{:02}", seconds as u64 / 60, seconds as u64 % 60)
}

fn safe_filename(title: &str) -> String {
    let name: String = title
        .chars()
        .filter(|c| !matches!(c, '/' | '\\' | ':' | '\0'))
        .take(80)
        .collect();
    if name.trim().is_empty() {
        "ManimGX 영상".into()
    } else {
        name
    }
}

fn user_directory(name: &str, fallback: &Path) -> PathBuf {
    std::env::var_os("HOME")
        .map(PathBuf::from)
        .map(|home| home.join(name))
        .filter(|path| path.is_dir())
        .unwrap_or_else(|| fallback.into())
}

fn asset_path(name: &str) -> PathBuf {
    if let Ok(executable) = std::env::current_exe()
        && let Some(contents) = executable.parent().and_then(Path::parent)
    {
        let path = contents.join("Resources/assets").join(name);
        if path.is_file() {
            return path;
        }
    }
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("assets")
        .join(name)
}

#[cfg(test)]
mod tests {
    use super::Studio;
    use gpui_kit::{
        AppContext, TestAppContext,
        component::{ActiveTheme, Root},
        px, size,
        test::TestWindowExt,
    };

    #[gpui_kit::test]
    fn command_return_submits_from_the_focused_composer(cx: &mut TestAppContext) {
        cx.update(gpui_kit::init);
        let directory = tempfile::tempdir().unwrap();
        let mut studio = None;
        let handle = cx.open_window(size(px(1440.0), px(900.0)), |window, cx| {
            let view = cx.new(|cx| Studio::with_directory(directory.path().into(), window, cx));
            studio = Some(view.clone());
            Root::new(view, window, cx)
        });
        let studio = studio.unwrap();
        cx.update_window(handle.into(), |_, window, cx| {
            window.render_frame(cx);
            window.click("new-film", cx);
        })
        .unwrap();
        cx.run_until_parked();
        cx.update_window(handle.into(), |_, window, cx| {
            window.render_frame(cx);
            window.press("secondary-enter", cx);
        })
        .unwrap();
        cx.run_until_parked();
        cx.update(|cx| {
            assert!(
                studio
                    .read(cx)
                    .error
                    .as_ref()
                    .is_some_and(|error| error.contains("12,000"))
            );
            assert!(studio.read(cx).ai.job.is_none());
        });
    }

    #[gpui_kit::test]
    fn new_film_focuses_composer_and_preserves_drafts_between_projects(cx: &mut TestAppContext) {
        cx.update(gpui_kit::init);
        let directory = tempfile::tempdir().unwrap();
        let mut studio = None;
        let handle = cx.open_window(size(px(1440.0), px(900.0)), |window, cx| {
            let view = cx.new(|cx| Studio::with_directory(directory.path().into(), window, cx));
            studio = Some(view.clone());
            Root::new(view, window, cx)
        });
        let studio = studio.unwrap();
        cx.update_window(handle.into(), |_, window, cx| {
            window.render_frame(cx);
            window.click("new-film", cx);
        })
        .unwrap();
        cx.run_until_parked();
        cx.update_window(handle.into(), |_, window, cx| {
            window.render_frame(cx);
            window.input("빛의 굴절을 20초 영상으로 만들어 줘", cx);
        })
        .unwrap();
        cx.run_until_parked();
        cx.update(|cx| {
            let state = studio.read(cx);
            assert_eq!(state.current().lesson_id, "custom");
            assert!(state.current().source.is_empty());
            assert_eq!(
                state.current().prompt_draft,
                "빛의 굴절을 20초 영상으로 만들어 줘"
            );
            assert_eq!(state.inspector_tab, 0);
        });
        cx.update_window(handle.into(), |_, window, cx| {
            window.click("new-film", cx);
        })
        .unwrap();
        cx.run_until_parked();
        cx.update(|cx| {
            let state = studio.read(cx);
            assert!(state.current().prompt_draft.is_empty());
            assert_eq!(
                state.session.projects[4].prompt_draft,
                "빛의 굴절을 20초 영상으로 만들어 줘"
            );
        });
        cx.update(|cx| studio.update(cx, |studio, _| studio.prepare_to_quit()));
        let session = crate::project::Session::load(directory.path()).unwrap();
        assert_eq!(
            session.projects[4].prompt_draft,
            "빛의 굴절을 20초 영상으로 만들어 줘"
        );
    }

    #[gpui_kit::test]
    fn switching_lessons_retains_source_edits_and_updates_selection(cx: &mut TestAppContext) {
        cx.update(gpui_kit::init);
        let directory = tempfile::tempdir().unwrap();
        let mut studio = None;
        let handle = cx.open_window(size(px(1440.0), px(900.0)), |window, cx| {
            let view = cx.new(|cx| {
                let mut studio = Studio::with_directory(directory.path().into(), window, cx);
                studio.inspector_tab = 1;
                studio
            });
            studio = Some(view.clone());
            Root::new(view, window, cx)
        });
        let studio = studio.unwrap();
        let (first_id, second_id) = cx.update(|cx| {
            let state = studio.read(cx);
            (
                format!("project-{}", state.session.projects[0].id),
                format!("project-{}", state.session.projects[1].id),
            )
        });
        cx.update_window(handle.into(), |_, window, cx| {
            window.render_frame(cx);
            window.click("play", cx);
            assert!(!studio.read(cx).playing);
            assert!(studio.read(cx).preview().is_none());
            window.click("project-title", cx);
            window.press("secondary-a", cx);
            window.input("나의 미분 수업", cx);
        })
        .unwrap();
        cx.run_until_parked();
        cx.update_window(handle.into(), |_, window, cx| {
            window.click(second_id.clone(), cx);
        })
        .unwrap();
        cx.run_until_parked();
        cx.update(|cx| {
            assert_eq!(studio.read(cx).session.selected, 1);
            assert_eq!(studio.read(cx).session.projects[0].title, "나의 미분 수업");
        });
        cx.update_window(handle.into(), |_, window, cx| {
            window.click(first_id.clone(), cx);
        })
        .unwrap();
        cx.run_until_parked();
        cx.update_window(handle.into(), |_, window, cx| {
            window.render_frame(cx);
            assert_eq!(window.find("project-title").value(), Some("나의 미분 수업"));
        })
        .unwrap();
        cx.update(|cx| {
            studio.update(cx, |studio, _| studio.prepare_to_quit());
        });
        let session = crate::project::Session::load(directory.path()).unwrap();
        assert_eq!(session.projects[0].title, "나의 미분 수업");
    }

    #[gpui_kit::test]
    fn quality_and_theme_controls_work_in_the_real_view(cx: &mut TestAppContext) {
        cx.update(gpui_kit::init);
        let directory = tempfile::tempdir().unwrap();
        let mut studio = None;
        let handle = cx.open_window(size(px(1440.0), px(900.0)), |window, cx| {
            let view = cx.new(|cx| {
                let mut studio = Studio::with_directory(directory.path().into(), window, cx);
                studio.inspector_tab = 1;
                studio
            });
            studio = Some(view.clone());
            Root::new(view, window, cx)
        });
        let studio = studio.unwrap();
        cx.update_window(handle.into(), |_, window, cx| {
            window.render_frame(cx);
            let was_dark = cx.theme().is_dark();
            window.click("theme", cx);
            assert_ne!(cx.theme().is_dark(), was_dark);
            let button = window.find("render-film").bounds();
            assert!(button.size.width > px(200.0));
            assert!(button.top() >= px(0.0));
            window.click("quality-full", cx);
        })
        .unwrap();
        cx.run_until_parked();
        cx.update(|cx| assert_eq!(studio.read(cx).quality, crate::render_job::Quality::Full));
        cx.update_window(handle.into(), |_, window, cx| {
            window.click("quality-draft", cx);
        })
        .unwrap();
        cx.run_until_parked();
        cx.update(|cx| assert_eq!(studio.read(cx).quality, crate::render_job::Quality::Draft));
    }
}

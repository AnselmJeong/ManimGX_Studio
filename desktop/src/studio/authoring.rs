use super::*;
use crate::{
    ai_job::{AiEvent, AiJob, Connection},
    project::ScenePlan,
};
use gpui_kit::component::input::{Textarea, TextareaState};

pub(super) struct Authoring {
    pub prompt: Entity<TextareaState>,
    pub job: Option<AiJob>,
    pub connection: Connection,
    pub settings: bool,
    pub plan: Vec<ScenePlan>,
    pub summary: String,
    pub origin: Option<(String, String)>,
    pub cancelling: bool,
}
impl Authoring {
    pub fn new(draft: &str, window: &mut Window, cx: &mut Context<Studio>) -> Self {
        Self {
            prompt: cx.new(|cx| {
                TextareaState::new(window, cx)
                    .rows(4)
                    .placeholder("만들고 싶은 영상이나 수정할 내용을 적어주세요")
                    .default_value(draft.to_owned())
            }),
            job: None,
            connection: Connection::default(),
            settings: false,
            plan: Vec::new(),
            summary: String::new(),
            origin: None,
            cancelling: false,
        }
    }
}
impl Studio {
    pub(super) fn busy(&self) -> bool {
        self.job.is_some() || self.ai.job.is_some()
    }

    pub(super) fn new_film(&mut self, _: &NewFilm, window: &mut Window, cx: &mut Context<Self>) {
        if self.busy() {
            return;
        }
        if self.session.projects.len() >= 100 {
            self.error = Some("프로젝트는 최대 100개까지 열 수 있습니다.".into());
            cx.notify();
            return;
        }
        self.session.projects.push(Project::blank());
        self.previews.push(None);
        self.paths.push(None);
        self.session.selected = self.session.projects.len() - 1;
        self.inspector_tab = 0;
        self.error = None;
        self.sync_editor(window, cx);
        self.ai.prompt.focus_handle(cx).focus(window, cx);
        self.status = "만들고 싶은 내용을 적으면 장면 구성부터 영상 생성까지 진행합니다".into();
        self.mark_changed(cx);
    }

    pub(super) fn start_ai(&mut self, action: &str, cx: &mut Context<Self>) {
        if self.busy() {
            return;
        }
        let prompt = self.ai.prompt.read(cx).value().to_string();
        if action == "create" && (prompt.trim().is_empty() || prompt.chars().count() > 12000) {
            self.error = Some("만들거나 수정할 내용을 12,000자 이내로 입력하세요.".into());
            cx.notify();
            return;
        }
        let request = serde_json::json!({"action":action, "data":self.directory, "model":self.session.ai_model, "project":self.current(), "prompt":prompt, "resolution":self.quality.resolution(), "seconds":self.seconds, "frame":self.preview().map(|preview| preview.frame_path(self.seconds))});
        match Runtime::discover().and_then(|runtime| AiJob::start(runtime, request)) {
            Ok(job) => {
                self.ai.job = Some(job);
                self.ai.cancelling = false;
                self.ai.origin = if action == "create" {
                    Some((self.current().id.clone(), self.current().source.clone()))
                } else {
                    None
                };
                self.ai.plan.clear();
                self.ai.summary.clear();
                self.error = None;
                self.status = if action == "create" {
                    "AI가 영상 제작을 준비하고 있습니다"
                } else {
                    "Codex 연결 확인 중"
                }
                .into();
            }
            Err(error) => self.error = Some(format!("{error:#}")),
        }
        cx.notify();
    }
    pub(super) fn generate_film(
        &mut self,
        _: &GenerateFilm,
        _: &mut Window,
        cx: &mut Context<Self>,
    ) {
        self.start_ai("create", cx);
    }

    pub(super) fn cancel_ai(&mut self, cx: &mut Context<Self>) {
        if let Some(job) = &self.ai.job {
            job.cancel();
            self.ai.cancelling = true;
            self.status = "작업을 중단하고 있습니다".into();
            cx.notify();
        }
    }

    pub(super) fn poll_ai(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let events: Vec<_> = self
            .ai
            .job
            .as_ref()
            .map(|job| job.events.try_iter().collect())
            .unwrap_or_default();
        for event in events {
            match event {
                AiEvent::Connection(connection) => self.ai.connection = connection,
                AiEvent::Login { url } => {
                    // The worker validates the exact OAuth host before emitting this URL.
                    if !self.ai.cancelling {
                        cx.open_url(&url);
                        self.status = "브라우저에서 ChatGPT 로그인을 완료하세요".into();
                    }
                }
                AiEvent::Phase { message } => {
                    if !self.ai.cancelling {
                        self.status = message;
                    }
                }
                AiEvent::Plan { scenes, summary } => {
                    self.ai.plan = scenes;
                    self.ai.summary = summary;
                }
                AiEvent::Result { project } => {
                    let current = self.current();
                    let matches = self.ai.origin.as_ref().is_some_and(|(id, source)| {
                        id == &current.id && source == &current.source && project.id == *id
                    });
                    if !matches || self.ai.cancelling {
                        continue;
                    }
                    match project.validate().and_then(|()| {
                        Preview::restore(&project, &self.directory)
                            .ok_or_else(|| anyhow::anyhow!("생성된 MP4를 확인하지 못했습니다."))
                    }) {
                        Ok(preview) => {
                            let duration = preview.duration;
                            *self.current_mut() = *project;
                            self.previews[self.session.selected] = Some(preview);
                            self.sync_editor(window, cx);
                            self.seconds = duration * 0.55;
                            self.position
                                .update(cx, |state, cx| state.set_value(55.0, window, cx));
                            self.ai.plan.clear();
                            self.ai.summary.clear();
                            self.status = "영상 생성 완료 · 재생하면서 대화로 수정해 보세요".into();
                            self.mark_changed(cx);
                        }
                        Err(error) => self.error = Some(format!("{error:#}")),
                    }
                }
                AiEvent::Error { message } => {
                    self.ai.job = None;
                    self.ai.origin = None;
                    self.ai.plan.clear();
                    self.ai.summary.clear();
                    self.status =
                        "AI 작업을 완료하지 못했습니다 · 요청과 이전 영상은 보관됩니다".into();
                    self.error = Some(message);
                }
                AiEvent::Cancelled => {
                    self.ai.job = None;
                    self.ai.origin = None;
                    self.ai.plan.clear();
                    self.ai.summary.clear();
                    self.status = "작업을 중단했습니다 · 요청과 이전 영상은 보관됩니다".into();
                }
                AiEvent::Done => {
                    self.ai.job = None;
                    if self.ai.origin.is_none() {
                        self.status = if self.ai.connection.connected {
                            "Codex 연결됨"
                        } else {
                            "AI 연결에서 ChatGPT로 로그인하세요"
                        }
                        .into();
                    }
                    self.ai.origin = None;
                }
            }
            cx.notify();
        }
    }

    fn restore_ai_revision(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.busy() {
            return;
        }
        if self.current_mut().restore_revision() {
            self.previews[self.session.selected] =
                Preview::restore(self.current(), &self.directory);
            self.sync_editor(window, cx);
            self.status = "이전 버전으로 복원했습니다".into();
            self.mark_changed(cx);
        }
    }

    pub(super) fn render_authoring(&self, cx: &mut Context<Self>) -> impl IntoElement {
        let busy = self.busy();
        v_flex().size_full().min_h_0().min_w_0()
            .child(h_flex().p_3().gap_2().justify_between()
                .child(div().text_xs().text_color(cx.theme().muted_foreground).child(if self.ai.connection.connected { "Codex · ChatGPT 구독" } else { "AI 연결 필요" }))
                .child(Button::new("ai-settings").ghost().small().label("AI 연결").selected(self.ai.settings)
                    .on_click(cx.listener(|this, _, _, cx| { this.ai.settings = !this.ai.settings; if this.ai.settings && this.ai.connection.cli.is_empty() { this.start_ai("status", cx); } cx.notify(); }))))
            .child(if self.ai.settings {
                self.render_ai_connection(cx).into_any_element()
            } else {
                v_flex().id("conversation-scroll").flex_1().min_h_0().overflow_y_scroll()
                    .child(v_flex().p_4().gap_4()
                        .when(self.current().conversation.is_empty(), |view| view.child(
                            v_flex().gap_3()
                                .child(div().text_lg().font_weight(FontWeight::SEMIBOLD).child("어떤 영상을 만들까요?"))
                                .child(div().text_sm().child("주제와 대상, 길이를 적어주세요. AI가 장면을 구성하고 영상을 만듭니다."))
                                .child(div().text_sm().text_color(cx.theme().muted_foreground).child("예: 태양과 지구의 계절 변화를 중학생에게 설명하는 30초 영상. 지구의 기울기를 강조해 줘."))
                                .child(div().text_xs().text_color(cx.theme().muted_foreground).child("완성 후에는 ‘두 번째 장면을 더 천천히’처럼 수정할 수 있습니다. 현재는 자막이 있는 무음 영상을 만듭니다."))))
                        .children(self.current().conversation.iter().map(|message| {
                            v_flex().id(SharedString::from(format!("message-{}", message.id))).gap_2()
                                .child(div().text_xs().font_weight(FontWeight::SEMIBOLD).text_color(cx.theme().muted_foreground).child(match message.role.as_str() { "user" => "나", "assistant" => "AI", _ => "프로젝트" }))
                                .child(div().text_sm().line_height(relative(1.5)).child(message.text.clone()))
                        }))
                        .when(self.ai.origin.is_some(), |view| view.child(div().id("ai-progress").text_sm().role(Role::Status).child(self.status.clone())))
                        .when_some(self.error.as_ref(), |view, error| view.child(div().text_sm().text_color(cx.theme().danger).child(error.clone()))))
                    .into_any_element()
            })
            .child(v_flex().p_3().gap_2().border_t_1().border_color(cx.theme().border)
                .child(label(if self.current().source.is_empty() { "만들 영상" } else { "만들거나 수정할 내용" }, cx))
                .child(Textarea::new(&self.ai.prompt).accessibility_id("ai-prompt").aria_label("영상 제작 요청").readonly(busy))
                .child(h_flex().gap_2()
                    .child(if self.ai.job.is_some() {
                        Button::new("cancel-ai").label(if self.ai.origin.is_some() { "생성 중단" } else { "연결 취소" }).disabled(self.ai.cancelling).on_click(cx.listener(|this, _, _, cx| this.cancel_ai(cx))).into_any_element()
                    } else {
                        Button::new("generate-ai").primary().label(if self.current().source.is_empty() { "AI로 영상 만들기" } else { "AI로 수정하기" }).disabled(busy || self.ai.prompt.read(cx).value().trim().is_empty()).tooltip("⌘↵")
                            .on_click(cx.listener(|this, _, window, cx| this.generate_film(&GenerateFilm, window, cx))).into_any_element()
                    })
                    .child(Button::new("restore-ai").ghost().small().label("이전 버전").disabled(busy || self.current().revisions.is_empty())
                        .on_click(cx.listener(|this, _, window, cx| this.restore_ai_revision(window, cx)))))
                .child(div().text_xs().text_color(cx.theme().muted_foreground).child("요청·장면 구성·현재 미리보기 프레임을 AI에 전달합니다")))
    }

    fn render_ai_connection(&self, cx: &mut Context<Self>) -> impl IntoElement {
        let busy = self.busy();
        v_flex().id("ai-connection-scroll").flex_1().min_h_0().overflow_y_scroll()
            .child(v_flex().p_4().gap_3()
                .child(div().font_weight(FontWeight::SEMIBOLD).child("Codex · ChatGPT 구독"))
                .child(div().text_sm().child(if self.ai.connection.connected { self.ai.connection.usage.clone() } else { "Studio 전용 ChatGPT 로그인이 필요합니다. 로그인은 브라우저에서 진행합니다.".into() }))
                .child(h_flex().gap_2()
                    .child(Button::new("ai-login").label(if self.ai.connection.connected { "로그아웃" } else { "ChatGPT 로그인…" }).disabled(busy)
                        .on_click(cx.listener(|this, _, _, cx| this.start_ai(if this.ai.connection.connected { "logout" } else { "login" }, cx))))
                    .child(Button::new("ai-refresh").ghost().label("새로고침").disabled(busy).on_click(cx.listener(|this, _, _, cx| this.start_ai("status", cx)))))
                .child(div().text_xs().text_color(cx.theme().muted_foreground).child("다른 Codex 앱과 계정 사용량을 공유합니다. 유료 API로 자동 전환하지 않습니다."))
                .child(label("모델", cx))
                .child(Button::new("ai-model-default").ghost().label("계정 기본 모델").selected(self.session.ai_model.is_empty()).disabled(busy)
                    .on_click(cx.listener(|this, _, _, cx| { this.session.ai_model.clear(); this.mark_changed(cx); })))
                .children(self.ai.connection.models.iter().map(|model| {
                    let slug = model.model.clone();
                    Button::new(SharedString::from(format!("ai-model-{slug}"))).ghost().label(model.name.clone()).selected(self.session.ai_model == slug).disabled(busy)
                        .on_click(cx.listener(move |this, _, _, cx| { this.session.ai_model = slug.clone(); this.mark_changed(cx); }))
                }))
                .child(div().text_xs().text_color(cx.theme().muted_foreground).child(format!("{}\n{}", self.ai.connection.version, self.ai.connection.cli)))
                .when_some(self.error.as_ref(), |view, error| view.child(div().text_sm().text_color(cx.theme().danger).child(error.clone()))))
    }
}

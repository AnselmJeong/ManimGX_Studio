use std::{
    fs,
    io::Write,
    path::{Path, PathBuf},
};

use anyhow::{Context, Result, bail};
use serde::{Deserialize, Serialize};

use crate::catalog::{LESSONS, Lesson};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub(crate) struct Project {
    pub version: u32,
    #[serde(default = "new_id")]
    pub id: String,
    pub lesson_id: String,
    pub title: String,
    pub scene: String,
    pub source: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub last_render: Option<String>,
    #[serde(default)]
    pub plan: Vec<ScenePlan>,
    #[serde(default)]
    pub summary: String,
    #[serde(default)]
    pub conversation: Vec<Message>,
    #[serde(default)]
    pub prompt_draft: String,
    #[serde(default)]
    pub revisions: Vec<Revision>,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub(crate) struct ScenePlan {
    pub title: String,
    pub description: String,
    pub seconds: f64,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub(crate) struct Message {
    pub id: String,
    pub role: String,
    pub text: String,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub(crate) struct Revision {
    pub title: String,
    pub source: String,
    pub scene: String,
    pub plan: Vec<ScenePlan>,
    pub summary: String,
    pub last_render: Option<String>,
}

impl Project {
    pub fn from_lesson(lesson: &Lesson) -> Self {
        Self {
            version: 1,
            id: new_id(),
            lesson_id: lesson.id.into(),
            title: lesson.title.into(),
            scene: "Lesson".into(),
            source: lesson.source.into(),
            last_render: None,
            plan: Vec::new(),
            summary: String::new(),
            conversation: Vec::new(),
            prompt_draft: String::new(),
            revisions: Vec::new(),
        }
    }

    pub fn blank() -> Self {
        let mut project = Self::from_lesson(&LESSONS[0]);
        project.lesson_id = "custom".into();
        project.title = "새 영상".into();
        project.source.clear();
        project
    }

    pub fn restore_revision(&mut self) -> bool {
        let Some(revision) = self.revisions.pop() else {
            return false;
        };
        self.title = revision.title;
        self.source = revision.source;
        self.scene = revision.scene;
        self.plan = revision.plan;
        self.summary = revision.summary;
        self.last_render = revision.last_render;
        self.conversation.push(Message {
            id: new_id(),
            role: "system".into(),
            text: "이전 버전으로 복원했습니다.".into(),
        });
        true
    }

    pub fn validate(&self) -> Result<()> {
        if self.version != 1 {
            bail!(
                "이 프로젝트 형식은 지원되지 않습니다 (버전 {}).",
                self.version
            );
        }
        if self.source.len() > 2_000_000 {
            bail!("코드는 2 MB 이하로 저장해 주세요.");
        }
        if self.source.trim().is_empty() && self.lesson_id != "custom" {
            bail!("렌더링할 Python 코드가 없습니다.");
        }
        if !valid_identifier(&self.scene) {
            bail!("장면 이름은 영문자 또는 밑줄로 시작하는 Python 클래스 이름이어야 합니다.");
        }
        if self.prompt_draft.len() > 48_000
            || self.conversation.len() > 110
            || self.revisions.len() > 10
            || self.plan.len() > 20
        {
            bail!("프로젝트 대화 또는 버전 기록이 너무 큽니다.");
        }
        if self
            .plan
            .iter()
            .any(|scene| !scene.seconds.is_finite() || scene.seconds <= 0.0)
        {
            bail!("장면 길이가 유효하지 않습니다.");
        }
        Ok(())
    }

    pub fn save(&self, path: &Path) -> Result<()> {
        self.validate()?;
        atomic_write(path, &serde_json::to_vec_pretty(self)?)
    }

    pub fn load(path: &Path) -> Result<Self> {
        if fs::metadata(path)?.len() > 8_000_000 {
            bail!("프로젝트 파일이 너무 큽니다 (최대 8 MB).");
        }
        let project: Self = serde_json::from_slice(&fs::read(path)?)
            .context("프로젝트 JSON을 읽을 수 없습니다.")?;
        project.validate()?;
        Ok(project)
    }

    pub fn parameter(&self, name: &str) -> Option<f32> {
        self.source.lines().find_map(|line| {
            let value = line
                .strip_prefix(&format!("{name} = "))?
                .trim()
                .parse::<f32>()
                .ok()?;
            value.is_finite().then_some(value)
        })
    }

    pub fn set_parameter(&mut self, name: &str, value: f32) -> bool {
        if !value.is_finite() || self.parameter(name).is_none() {
            return false;
        }
        let prefix = format!("{name} = ");
        self.source = self
            .source
            .lines()
            .map(|line| {
                if line.starts_with(&prefix) {
                    format!("{name} = {value:.2}")
                } else {
                    line.to_owned()
                }
            })
            .collect::<Vec<_>>()
            .join("\n")
            + "\n";
        true
    }
}

pub(crate) fn new_id() -> String {
    static NEXT: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let stamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    format!(
        "{stamp:x}-{:x}",
        NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
    )
}

fn valid_identifier(name: &str) -> bool {
    let mut chars = name.chars();
    chars
        .next()
        .is_some_and(|c| c.is_ascii_alphabetic() || c == '_')
        && chars.all(|c| c.is_ascii_alphanumeric() || c == '_')
}

pub(crate) fn atomic_write(path: &Path, bytes: &[u8]) -> Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let temporary = path.with_file_name(format!(".manimgx-{}.tmp", new_id()));
    let result = (|| -> Result<()> {
        let mut file = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)?;
        file.write_all(bytes)?;
        file.sync_all()?;
        fs::rename(&temporary, path)?;
        Ok(())
    })();
    if result.is_err() {
        let _ = fs::remove_file(temporary);
    }
    result.with_context(|| format!("{}에 저장할 수 없습니다.", path.display()))
}

#[derive(Serialize, Deserialize)]
pub(crate) struct Session {
    pub selected: usize,
    pub projects: Vec<Project>,
    #[serde(default)]
    pub pane_widths: Vec<f32>,
    #[serde(default)]
    pub ai_model: String,
}

impl Default for Session {
    fn default() -> Self {
        Self {
            selected: 0,
            projects: LESSONS.iter().map(Project::from_lesson).collect(),
            pane_widths: Vec::new(),
            ai_model: String::new(),
        }
    }
}

impl Session {
    pub fn load(directory: &Path) -> Result<Self> {
        let path = directory.join("session.json");
        if !path.exists() {
            return Ok(Self::default());
        }
        if fs::metadata(&path)?.len() > 64_000_000 {
            bail!("자동 저장 파일이 너무 큽니다.");
        }
        let session: Self = serde_json::from_slice(&fs::read(path)?)?;
        if session.projects.is_empty()
            || session.projects.len() > 100
            || session.selected >= session.projects.len()
        {
            bail!("자동 저장의 프로젝트 목록을 읽을 수 없습니다.");
        }
        // Keep incomplete source edits: only structural limits apply to draft recovery.
        if session
            .projects
            .iter()
            .any(|project| project.version != 1 || project.source.len() > 2_000_000)
        {
            bail!("자동 저장 형식을 확인해 주세요.");
        }
        Ok(session)
    }

    pub fn save(&self, directory: &Path) -> Result<()> {
        atomic_write(
            &directory.join("session.json"),
            &serde_json::to_vec_pretty(self)?,
        )
    }
}

pub(crate) fn data_directory() -> PathBuf {
    if let Some(directory) = std::env::var_os("MANIMGX_STUDIO_DATA") {
        return PathBuf::from(directory);
    }
    let home = std::env::var_os("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(std::env::temp_dir);
    home.join("Library/Application Support/ManimGX Studio")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn blank_ai_projects_and_revision_history_round_trip() {
        let directory = tempfile::tempdir().unwrap();
        let mut project = Project::blank();
        project.prompt_draft = "빛의 굴절을 설명해 줘".into();
        project.save(&directory.path().join("draft.mgx")).unwrap();
        assert_eq!(
            Project::load(&directory.path().join("draft.mgx")).unwrap(),
            project
        );
        project.revisions.push(Revision {
            title: "first".into(),
            source: "first source".into(),
            scene: "Lesson".into(),
            plan: Vec::new(),
            summary: "first plan".into(),
            last_render: Some("123-456".into()),
        });
        project.source = "second source".into();
        project.save(&directory.path().join("draft.mgx")).unwrap();
        let mut restored = Project::load(&directory.path().join("draft.mgx")).unwrap();
        assert!(restored.restore_revision());
        assert_eq!(restored.source, "first source");
        assert_eq!(restored.last_render.as_deref(), Some("123-456"));
        assert_eq!(restored.prompt_draft, "빛의 굴절을 설명해 줘");
    }

    #[test]
    fn legacy_projects_load_without_ai_fields() {
        let old = serde_json::json!({"version":1,"id":"legacy","lesson_id":"wave","title":"old","scene":"Lesson","source":"old code"});
        let project: Project = serde_json::from_value(old).unwrap();
        project.validate().unwrap();
        assert!(project.conversation.is_empty());
        assert!(project.revisions.is_empty());
    }

    #[test]
    fn saved_project_round_trips_unicode_and_custom_code() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("한글 프로젝트.mgx");
        let mut project = Project::from_lesson(&LESSONS[0]);
        project.source.push_str("\n# 사용자 메모\n");
        project.save(&path).unwrap();
        assert_eq!(Project::load(&path).unwrap(), project);
    }

    #[test]
    fn parameter_update_preserves_the_users_scene_and_rejects_expressions() {
        let mut project = Project::from_lesson(&LESSONS[0]);
        project.source.push_str("# Keep this custom animation\n");
        assert!(project.set_parameter("VALUE", 1.7));
        assert_eq!(project.parameter("VALUE"), Some(1.7));
        assert!(project.source.ends_with("# Keep this custom animation\n"));
        project.source = "VALUE = math.pi\n".into();
        assert!(!project.set_parameter("VALUE", 2.0));
        assert_eq!(project.source, "VALUE = math.pi\n");
        assert!(!project.set_parameter("VALUE", f32::NAN));
    }

    #[test]
    fn validation_rejects_bad_scene_names_and_future_formats() {
        let mut project = Project::from_lesson(&LESSONS[0]);
        project.scene = "Lesson; touch /tmp/unsafe".into();
        assert!(project.validate().is_err());
        project.scene = "Lesson".into();
        project.version = 2;
        assert!(project.validate().is_err());
    }

    #[test]
    fn session_restores_incomplete_edits_and_selection() {
        let directory = tempfile::tempdir().unwrap();
        let mut session = Session {
            selected: 2,
            ..Default::default()
        };
        session.projects[2].source = "def unfinished(".into();
        session.save(directory.path()).unwrap();
        let loaded = Session::load(directory.path()).unwrap();
        assert_eq!(loaded.selected, 2);
        assert_eq!(loaded.projects[2].source, "def unfinished(");
    }
}

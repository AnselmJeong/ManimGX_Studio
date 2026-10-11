use std::{
    fs::{self, File},
    path::{Path, PathBuf},
    process::{Command, Stdio},
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
        mpsc::{self, Receiver, Sender},
    },
    thread,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

use anyhow::{Context, Result, bail};
use serde::Deserialize;

use crate::project::Project;

#[derive(Clone)]
pub(crate) struct Runtime {
    pub(crate) python: PathBuf,
    pub(crate) worker: PathBuf,
}

impl Runtime {
    pub fn discover() -> Result<Self> {
        let executable = std::env::current_exe()?;
        if let Some(contents) = executable.parent().and_then(Path::parent) {
            let resources = contents.join("Resources");
            let python = resources.join("python/bin/python3");
            let worker = resources.join("worker.py");
            if python.is_file() && worker.is_file() {
                return Ok(Self { python, worker });
            }
        }
        let root = Path::new(env!("CARGO_MANIFEST_DIR"));
        let python = std::env::var_os("MANIMGX_STUDIO_PYTHON")
            .map(PathBuf::from)
            .unwrap_or_else(|| root.join("../.venv/bin/python"));
        let worker = root.join("runtime/worker.py");
        if !python.is_file() {
            bail!("Python 실행 환경이 없습니다. desktop/README.md의 설치 단계를 실행해 주세요.");
        }
        Ok(Self { python, worker })
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) enum Quality {
    Draft,
    Full,
}

impl Quality {
    pub fn resolution(self) -> &'static str {
        match self {
            Self::Draft => "1280x720",
            Self::Full => "1920x1080",
        }
    }
    pub fn label(self) -> &'static str {
        match self {
            Self::Draft => "720p 초안",
            Self::Full => "1080p 완성본",
        }
    }
}

#[derive(Clone, Deserialize)]
pub(crate) struct Preview {
    pub duration: f64,
    pub width: u32,
    pub height: u32,
    pub fps: f64,
    pub frames: Vec<String>,
    pub times: Vec<f64>,
    #[serde(skip)]
    pub directory: PathBuf,
    #[serde(skip)]
    pub source: String,
    #[serde(skip)]
    pub scene: String,
}

impl Preview {
    pub fn restore(project: &Project, data: &Path) -> Option<Self> {
        let key = project.last_render.as_deref()?;
        if key.is_empty() || !key.bytes().all(|c| c.is_ascii_digit() || c == b'-') {
            return None;
        }
        let directory = data.join("renders").join(key);
        let rendered = Project::load(&directory.join("project.mgx")).ok()?;
        Self::load(&directory, rendered.source, rendered.scene).ok()
    }

    fn load(directory: &Path, source: String, scene: String) -> Result<Self> {
        let mut preview: Self = serde_json::from_slice(&fs::read(directory.join("preview.json"))?)?;
        if !preview.duration.is_finite()
            || preview.duration <= 0.0
            || preview.frames.is_empty()
            || preview.frames.len() > 240
            || preview.frames.len() != preview.times.len()
            || preview
                .times
                .iter()
                .any(|t| !t.is_finite() || *t < 0.0 || *t > preview.duration)
            || preview.times.windows(2).any(|t| t[0] > t[1])
        {
            bail!("영상 미리보기 정보를 읽을 수 없습니다.");
        }
        for name in &preview.frames {
            if Path::new(name).components().count() != 1
                || !name.starts_with("frame-")
                || !directory.join(name).is_file()
            {
                bail!("미리보기 프레임이 없습니다: {name}");
            }
        }
        let movie = directory.join("film.mp4");
        if fs::metadata(movie)?.len() == 0 {
            bail!("MP4가 비어 있습니다.");
        }
        preview.directory = directory.into();
        preview.source = source;
        preview.scene = scene;
        Ok(preview)
    }

    pub fn frame_at(&self, seconds: f64) -> usize {
        self.times
            .partition_point(|time| *time <= seconds)
            .saturating_sub(1)
            .min(self.frames.len().saturating_sub(1))
    }

    pub fn frame_path(&self, seconds: f64) -> PathBuf {
        self.directory.join(&self.frames[self.frame_at(seconds)])
    }
    pub fn movie(&self) -> PathBuf {
        self.directory.join("film.mp4")
    }

    pub fn export(&self, destination: &Path) -> Result<()> {
        let temporary =
            destination.with_file_name(format!(".manimgx-{}.mp4", crate::project::new_id()));
        let result = (|| -> Result<()> {
            fs::copy(self.movie(), &temporary)?;
            fs::rename(&temporary, destination)?;
            Ok(())
        })();
        if result.is_err() {
            let _ = fs::remove_file(temporary);
        }
        result
    }
}

pub(crate) enum RenderEvent {
    Phase(String),
    Finished(Result<Preview>),
    Cancelled,
}

pub(crate) struct RenderJob {
    pub events: Receiver<RenderEvent>,
    pub started: Instant,
    cancelled: Arc<AtomicBool>,
}

impl RenderJob {
    pub fn start(
        runtime: Runtime,
        project: Project,
        quality: Quality,
        data: &Path,
    ) -> Result<Self> {
        project.validate()?;
        if project.source.trim().is_empty() {
            bail!("AI 제작에서 내용을 입력해 먼저 영상을 만들어주세요.");
        }
        let stamp = SystemTime::now().duration_since(UNIX_EPOCH)?.as_nanos();
        let directory = data
            .join("renders")
            .join(format!("{stamp}-{}", std::process::id()));
        fs::create_dir_all(&directory)?;
        fs::write(directory.join("scene.py"), &project.source)?;
        project.save(&directory.join("project.mgx"))?;
        let (sender, events) = mpsc::channel();
        let cancelled = Arc::new(AtomicBool::new(false));
        let signal = cancelled.clone();
        let run = directory.clone();
        thread::spawn(move || {
            let result = run_process(&runtime, &project, quality, &run, &signal, &sender);
            if signal.load(Ordering::Relaxed) {
                let _ = sender.send(RenderEvent::Cancelled);
            } else {
                let _ = sender.send(RenderEvent::Finished(result));
            }
        });
        Ok(Self {
            events,
            started: Instant::now(),
            cancelled,
        })
    }

    pub fn cancel(&self) {
        self.cancelled.store(true, Ordering::Relaxed);
    }
}

impl Drop for RenderJob {
    fn drop(&mut self) {
        self.cancel();
    }
}

fn run_process(
    runtime: &Runtime,
    project: &Project,
    quality: Quality,
    directory: &Path,
    cancelled: &AtomicBool,
    sender: &Sender<RenderEvent>,
) -> Result<Preview> {
    let log = File::create(directory.join("render.log"))?;
    let mut child = Command::new(&runtime.python)
        .arg("-u")
        .arg(&runtime.worker)
        .arg(directory)
        .arg(quality.resolution())
        .arg("30")
        .arg(&project.scene)
        .current_dir(directory)
        .env("PYTHONNOUSERSITE", "1")
        .env_remove("PYTHONPATH")
        .env_remove("PYTHONHOME")
        .stdin(Stdio::null())
        .stdout(log.try_clone()?)
        .stderr(log)
        .spawn()
        .context("렌더러를 시작하지 못했습니다.")?;
    let started = Instant::now();
    let mut phase = String::new();
    loop {
        if cancelled.load(Ordering::Relaxed) || started.elapsed() > Duration::from_secs(1800) {
            let _ = child.kill();
            let _ = child.wait();
            bail!("렌더링이 중단되었습니다 (최대 실행 시간 30분).");
        }
        if let Some(status) = child.try_wait()? {
            if !status.success() {
                let log = fs::read_to_string(directory.join("render.log")).unwrap_or_default();
                let tail = log
                    .lines()
                    .rev()
                    .take(24)
                    .collect::<Vec<_>>()
                    .into_iter()
                    .rev()
                    .collect::<Vec<_>>()
                    .join("\n");
                bail!("렌더링에 실패했습니다. 코드를 확인하고 다시 실행해 주세요.\n\n{tail}");
            }
            return Preview::load(directory, project.source.clone(), project.scene.clone())
                .context("렌더러 결과를 확인하지 못했습니다.");
        }
        if let Ok(bytes) = fs::read(directory.join("status.json"))
            && let Ok(status) = serde_json::from_slice::<serde_json::Value>(&bytes)
            && let Some(next) = status["phase"].as_str()
            && phase != next
        {
            phase = next.into();
            let _ = sender.send(RenderEvent::Phase(phase.clone()));
        }
        thread::sleep(Duration::from_millis(100));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::catalog::LESSONS;

    #[test]
    fn preview_seeks_to_previous_sample() {
        let preview = Preview {
            duration: 3.0,
            width: 1,
            height: 1,
            fps: 30.0,
            frames: vec!["a".into(), "b".into(), "c".into()],
            times: vec![0.0, 1.0, 2.0],
            directory: PathBuf::new(),
            source: String::new(),
            scene: String::new(),
        };
        assert_eq!(preview.frame_at(-1.0), 0);
        assert_eq!(preview.frame_at(1.8), 1);
        assert_eq!(preview.frame_at(9.0), 2);
    }

    #[test]
    fn failures_surface_stderr_and_do_not_claim_a_video() {
        let directory = tempfile::tempdir().unwrap();
        let worker = directory.path().join("failing.sh");
        fs::write(&worker, "echo 'Intentional render failure' >&2\nexit 7\n").unwrap();
        let runtime = Runtime {
            python: "/bin/sh".into(),
            worker,
        };
        let job = RenderJob::start(
            runtime,
            Project::from_lesson(&LESSONS[0]),
            Quality::Draft,
            directory.path(),
        )
        .unwrap();
        match job.events.recv_timeout(Duration::from_secs(5)).unwrap() {
            RenderEvent::Finished(Err(error)) => {
                assert!(error.to_string().contains("Intentional render failure"))
            }
            _ => panic!("Failed render must return an error"),
        }
    }

    #[test]
    fn cancellation_reaps_the_renderer() {
        let directory = tempfile::tempdir().unwrap();
        let worker = directory.path().join("waiting.sh");
        fs::write(&worker, "while :; do :; done\n").unwrap();
        let runtime = Runtime {
            python: "/bin/sh".into(),
            worker,
        };
        let job = RenderJob::start(
            runtime,
            Project::from_lesson(&LESSONS[0]),
            Quality::Draft,
            directory.path(),
        )
        .unwrap();
        job.cancel();
        assert!(matches!(
            job.events.recv_timeout(Duration::from_secs(5)).unwrap(),
            RenderEvent::Cancelled
        ));
    }

    #[test]
    fn restored_preview_keeps_its_rendered_source_and_export_failure_preserves_destination() {
        let directory = tempfile::tempdir().unwrap();
        let run = directory.path().join("renders/123-456");
        fs::create_dir_all(&run).unwrap();
        let original = Project::from_lesson(&LESSONS[0]);
        original.save(&run.join("project.mgx")).unwrap();
        fs::write(run.join("film.mp4"), b"fixture video").unwrap();
        fs::write(run.join("frame-0000.jpg"), b"fixture frame").unwrap();
        fs::write(run.join("preview.json"), r#"{"duration":2.0,"width":1280,"height":720,"fps":30,"frames":["frame-0000.jpg"],"times":[0.0]}"#).unwrap();
        let mut changed = original.clone();
        changed.source.push_str("# A newer edit\n");
        changed.last_render = Some("123-456".into());
        let preview = Preview::restore(&changed, directory.path()).unwrap();
        assert_eq!(preview.source, original.source);
        assert_ne!(preview.source, changed.source);
        let destination = directory.path().join("keep.mp4");
        fs::write(&destination, b"existing export").unwrap();
        fs::remove_file(preview.movie()).unwrap();
        assert!(preview.export(&destination).is_err());
        assert_eq!(fs::read(&destination).unwrap(), b"existing export");
        changed.last_render = Some("../elsewhere".into());
        assert!(Preview::restore(&changed, directory.path()).is_none());
    }
}

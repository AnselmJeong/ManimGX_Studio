use crate::{
    project::{Project, ScenePlan},
    render_job::Runtime,
};
use anyhow::{Context, Result};
use serde::Deserialize;
use std::{
    io::{BufRead, BufReader, Read, Write},
    process::{Command, Stdio},
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
        mpsc::{self, Receiver},
    },
    thread,
    time::{Duration, Instant},
};

#[derive(Clone, Deserialize, Default)]
pub(crate) struct Connection {
    pub connected: bool,
    pub models: Vec<Model>,
    pub usage: String,
    pub cli: String,
    pub version: String,
}
#[derive(Clone, Deserialize)]
pub(crate) struct Model {
    pub model: String,
    pub name: String,
}
#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub(crate) enum AiEvent {
    Phase {
        message: String,
    },
    Connection(Connection),
    Login {
        url: String,
    },
    Plan {
        scenes: Vec<ScenePlan>,
        summary: String,
    },
    Result {
        project: Box<Project>,
    },
    Error {
        message: String,
    },
    Cancelled,
    Done,
}
pub(crate) struct AiJob {
    pub events: Receiver<AiEvent>,
    cancelled: Arc<AtomicBool>,
    pub started: Instant,
}
impl AiJob {
    pub fn start(runtime: Runtime, request: serde_json::Value) -> Result<Self> {
        let worker = runtime.worker.with_file_name("ai_worker.py");
        let mut child = Command::new(&runtime.python)
            .arg("-u")
            .arg(worker)
            .env("PYTHONNOUSERSITE", "1")
            .env_remove("PYTHONPATH")
            .env_remove("PYTHONHOME")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .context("AI 작업을 시작하지 못했습니다.")?;
        let mut stdin = child.stdin.take().context("AI 입력 연결 실패")?;
        if let Err(error) = writeln!(stdin, "{request}") {
            let _ = child.kill();
            let _ = child.wait();
            return Err(error.into());
        }
        let stdout = child.stdout.take().context("AI 출력 연결 실패")?;
        let (sender, events) = mpsc::channel();
        let cancelled = Arc::new(AtomicBool::new(false));
        let signal = cancelled.clone();
        let output = sender.clone();
        thread::spawn(move || {
            let mut reader = BufReader::new(stdout);
            loop {
                let mut line = String::new();
                match reader.by_ref().take(3_000_001).read_line(&mut line) {
                    Ok(0) => break,
                    Ok(_) if line.len() <= 3_000_000 => match serde_json::from_str(&line) {
                        Ok(event) => {
                            let _ = output.send(event);
                        }
                        Err(_) => {
                            let _ = output.send(AiEvent::Error {
                                message: "AI 응답 형식을 읽지 못했습니다.".into(),
                            });
                            break;
                        }
                    },
                    _ => {
                        let _ = output.send(AiEvent::Error {
                            message: "AI 응답 크기 또는 연결 오류가 발생했습니다.".into(),
                        });
                        break;
                    }
                }
            }
        });
        thread::spawn(move || {
            let started = Instant::now();
            let mut cancelled_at = None;
            loop {
                if signal.load(Ordering::Relaxed) || started.elapsed() > Duration::from_secs(2400) {
                    if cancelled_at.is_none() {
                        let _ = writeln!(stdin, "cancel");
                        let _ = stdin.flush();
                        cancelled_at = Some(Instant::now());
                    }
                    if cancelled_at.is_some_and(|time| time.elapsed() > Duration::from_secs(5)) {
                        let _ = child.kill();
                        let _ = child.wait();
                        let _ = sender.send(AiEvent::Cancelled);
                        break;
                    }
                }
                match child.try_wait() {
                    Ok(Some(status)) => {
                        if !status.success() {
                            let _ = sender.send(AiEvent::Error {
                                message: format!(
                                    "AI 작업이 종료되었습니다 ({status}). 다시 시도하세요."
                                ),
                            });
                        }
                        break;
                    }
                    Err(error) => {
                        let _ = child.kill();
                        let _ = child.wait();
                        let _ = sender.send(AiEvent::Error {
                            message: error.to_string(),
                        });
                        break;
                    }
                    _ => thread::sleep(Duration::from_millis(100)),
                }
            }
        });
        Ok(Self {
            events,
            cancelled,
            started: Instant::now(),
        })
    }
    pub fn cancel(&self) {
        self.cancelled.store(true, Ordering::Relaxed);
    }
}
impl Drop for AiJob {
    fn drop(&mut self) {
        self.cancel();
    }
}

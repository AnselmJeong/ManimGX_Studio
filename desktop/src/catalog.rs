#[derive(Clone, Copy)]
pub(crate) struct Lesson {
    pub id: &'static str,
    pub title: &'static str,
    pub category: &'static str,
    pub question: &'static str,
    pub summary: &'static str,
    pub formula: &'static str,
    pub parameter: &'static str,
    pub unit: &'static str,
    pub range: (f32, f32, f32),
    pub initial: f32,
    pub steps: [(&'static str, &'static str); 3],
    pub source: &'static str,
}

pub(crate) const LESSONS: [Lesson; 4] = [
    Lesson {
        id: "derivative",
        title: "미분과 접선",
        category: "수학 · 미적분",
        question: "한순간의 변화는 어떻게 측정할까요?",
        summary: "두 점을 잇는 할선이 접선으로 바뀌는 과정을 따라가며, 미분을 순간 변화율로 이해합니다.",
        formula: "f(x) = x²   →   f′(x) = 2x",
        parameter: "접점을 놓을 x 좌표",
        unit: "",
        range: (0.4, 1.8, 0.1),
        initial: 1.0,
        steps: [
            ("함수 관찰", "포물선 위에서 두 점을 선택합니다."),
            (
                "변화 좁히기",
                "두 점 사이의 간격을 줄이며 기울기를 관찰합니다.",
            ),
            (
                "개념 연결",
                "할선의 극한이 접선이며, 그 기울기가 미분값입니다.",
            ),
        ],
        source: include_str!("../lessons/derivative.py"),
    },
    Lesson {
        id: "wave",
        title: "파동과 진동",
        category: "물리 · 파동",
        question: "물질은 제자리에 있는데 무엇이 이동할까요?",
        summary: "한 점의 진동과 파동 전체의 진행을 함께 보며, 진동수·파장·속력의 관계를 살펴봅니다.",
        formula: "y = A sin(kx − ωt)   ·   v = fλ",
        parameter: "진동수",
        unit: "Hz",
        range: (0.5, 2.0, 0.1),
        initial: 1.0,
        steps: [
            ("한 점 관찰", "노란 점은 수직 방향으로만 움직입니다."),
            ("전체 관찰", "파동의 모양은 오른쪽으로 진행합니다."),
            (
                "관계 찾기",
                "파장이 일정할 때, 진동수가 커지면 속력도 커집니다.",
            ),
        ],
        source: include_str!("../lessons/wave.py"),
    },
    Lesson {
        id: "pendulum",
        title: "진자의 주기",
        category: "물리 · 역학",
        question: "긴 진자는 왜 더 느리게 흔들릴까요?",
        summary: "이상적인 작은 진폭의 진자를 관찰하며, 길이와 중력이 왕복 시간에 미치는 영향을 알아봅니다.",
        formula: "T ≈ 2π √(L/g)",
        parameter: "진자의 길이",
        unit: "m",
        range: (0.5, 3.0, 0.1),
        initial: 1.5,
        steps: [
            ("운동 관찰", "한 번 왕복하는 데 걸리는 시간이 주기입니다."),
            (
                "길이 바꾸기",
                "길이를 늘리면 같은 시간 동안 더 적게 왕복합니다.",
            ),
            (
                "수식 연결",
                "길이가 4배면 주기는 약 2배. 작은 진폭에서의 근사입니다.",
            ),
        ],
        source: include_str!("../lessons/pendulum.py"),
    },
    Lesson {
        id: "pythagoras",
        title: "피타고라스 정리",
        category: "수학 · 기하",
        question: "세 변의 길이가 넓이로 연결된다면?",
        summary: "직각삼각형의 각 변 위에 정사각형을 만들고, 두 넓이의 합과 빗변 위의 넓이를 비교합니다.",
        formula: "a² + b² = c²",
        parameter: "밑변 a의 길이",
        unit: "",
        range: (1.0, 3.0, 0.1),
        initial: 2.0,
        steps: [
            (
                "도형 만들기",
                "직각삼각형의 세 변 위에 정사각형을 만듭니다.",
            ),
            (
                "넓이 비교",
                "각 정사각형의 넓이는 그 변의 길이의 제곱입니다.",
            ),
            (
                "정리 확인",
                "a² + b² = c² 관계를 수치로 확인합니다. 시각화이며 일반 증명은 아닙니다.",
            ),
        ],
        source: include_str!("../lessons/pythagoras.py"),
    },
];

pub(crate) fn lesson(id: &str) -> &'static Lesson {
    LESSONS
        .iter()
        .find(|lesson| lesson.id == id)
        .unwrap_or(&LESSONS[0])
}

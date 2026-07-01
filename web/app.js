const REAL_DATA_URL = "../data/questions.json";
const SAMPLE_DATA_URL = "../data/questions.sample.json";

const el = (id) => document.getElementById(id);

let rawQuestions = [];
let quiz = [];       // shuffled + prepared questions for this run
let current = 0;
let results = [];    // {question, options, correctIndices, selected, isCorrect}
let answered = false;

function shuffle(array) {
  const a = array.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function setStatus(msg) {
  el("loadStatus").textContent = msg;
}

async function tryFetch(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error("fetch failed");
  return res.json();
}

async function loadDefault() {
  try {
    rawQuestions = await tryFetch(REAL_DATA_URL);
    setStatus(`문제 ${rawQuestions.length}개를 불러왔습니다 (data/questions.json). 다른 문제를 쓰려면 위에서 JSON 파일을 선택하세요.`);
    return;
  } catch (e) {
    // data/questions.json이 없으면(아직 변환 전) 샘플로 폴백
  }
  try {
    rawQuestions = await tryFetch(SAMPLE_DATA_URL);
    setStatus(`샘플 문제 ${rawQuestions.length}개를 불러왔습니다. run_local.bat(또는 .sh)로 실제 덤프를 변환하면 자동으로 그 문제가 로드됩니다.`);
  } catch (e) {
    setStatus("문제를 자동으로 불러오지 못했습니다 (file:// 로 열면 발생 가능). 위에서 JSON 파일을 직접 선택해주세요.");
  }
}

el("fileInput").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      rawQuestions = JSON.parse(reader.result);
      setStatus(`"${file.name}"에서 문제 ${rawQuestions.length}개를 불러왔습니다.`);
    } catch (err) {
      setStatus("JSON 파싱에 실패했습니다. parser/parse_pdf.py로 생성한 파일인지 확인해주세요.");
    }
  };
  reader.readAsText(file);
});

function buildQuiz() {
  if (!rawQuestions.length) {
    alert("불러온 문제가 없습니다.");
    return false;
  }
  const shuffleOpts = el("shuffleOptions").checked;
  const countRaw = el("countInput").value;
  const count = countRaw ? Math.min(parseInt(countRaw, 10), rawQuestions.length) : rawQuestions.length;

  const pool = shuffle(rawQuestions).slice(0, count);

  quiz = pool.map((q) => {
    const indexed = q.options.map((text, idx) => ({ text, isCorrect: q.correct.includes(idx) }));
    const options = shuffleOpts ? shuffle(indexed) : indexed;
    return {
      id: q.id,
      question: q.question,
      options,
      isMultiple: q.correct.length > 1,
    };
  });

  current = 0;
  results = [];
  answered = false;
  return true;
}

function showScreen(name) {
  ["setup", "quiz", "result"].forEach((s) => el(s).classList.toggle("hidden", s !== name));
}

function renderQuestion() {
  answered = false;
  const q = quiz[current];
  el("progressText").textContent = `문제 ${current + 1} / ${quiz.length}`;
  el("questionText").textContent = q.question;

  const list = el("optionsList");
  list.innerHTML = "";
  q.options.forEach((opt, idx) => {
    const wrapper = document.createElement("label");
    wrapper.className = "option";
    wrapper.dataset.idx = idx;

    const input = document.createElement("input");
    input.type = q.isMultiple ? "checkbox" : "radio";
    input.name = "option";
    input.value = idx;

    const span = document.createElement("span");
    span.textContent = opt.text;

    wrapper.appendChild(input);
    wrapper.appendChild(span);
    list.appendChild(wrapper);
  });

  el("feedback").classList.add("hidden");
  el("feedback").textContent = "";
  el("submitBtn").classList.remove("hidden");
  el("submitBtn").disabled = false;
  el("nextBtn").classList.add("hidden");
}

function getSelectedIndices() {
  return Array.from(document.querySelectorAll('#optionsList input:checked')).map((i) => parseInt(i.value, 10));
}

function submitAnswer() {
  if (answered) return;
  const selected = getSelectedIndices();
  if (selected.length === 0) {
    alert("답을 선택해주세요.");
    return;
  }
  answered = true;

  const q = quiz[current];
  const correctIndices = q.options
    .map((o, idx) => (o.isCorrect ? idx : -1))
    .filter((idx) => idx !== -1);

  const isCorrect =
    selected.length === correctIndices.length &&
    selected.every((s) => correctIndices.includes(s));

  document.querySelectorAll("#optionsList .option").forEach((wrapper) => {
    const idx = parseInt(wrapper.dataset.idx, 10);
    if (correctIndices.includes(idx)) wrapper.classList.add("correct");
    else if (selected.includes(idx)) wrapper.classList.add("incorrect");
  });

  const feedback = el("feedback");
  feedback.classList.remove("hidden");
  feedback.className = `feedback ${isCorrect ? "good" : "bad"}`;
  feedback.textContent = isCorrect ? "정답입니다!" : "오답입니다.";

  el("submitBtn").classList.add("hidden");
  el("nextBtn").classList.remove("hidden");

  results.push({
    question: q.question,
    options: q.options,
    correctIndices,
    selected,
    isCorrect,
  });
}

function nextQuestion() {
  current += 1;
  if (current >= quiz.length) {
    showResult();
  } else {
    renderQuestion();
  }
}

function showResult() {
  const correctCount = results.filter((r) => r.isCorrect).length;
  el("scoreText").textContent = `${correctCount} / ${results.length} 정답`;

  const reviewList = el("reviewList");
  reviewList.innerHTML = "";
  results.forEach((r, i) => {
    const item = document.createElement("div");
    item.className = "review-item";
    const tag = r.isCorrect ? '<span class="tag good">정답</span>' : '<span class="tag bad">오답</span>';
    const correctText = r.correctIndices.map((idx) => r.options[idx].text).join(" / ");
    const selectedText = r.selected.map((idx) => r.options[idx].text).join(" / ");
    item.innerHTML = `
      <div>${tag} <strong>${i + 1}. ${r.question}</strong></div>
      <div style="margin-top:6px;color:var(--muted);">내 답: ${selectedText}</div>
      <div style="color:var(--good);">정답: ${correctText}</div>
    `;
    reviewList.appendChild(item);
  });

  showScreen("result");
}

el("startBtn").addEventListener("click", () => {
  if (buildQuiz()) {
    showScreen("quiz");
    renderQuestion();
  }
});
el("submitBtn").addEventListener("click", submitAnswer);
el("nextBtn").addEventListener("click", nextQuestion);
el("restartBtn").addEventListener("click", () => showScreen("setup"));

loadDefault();

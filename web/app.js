const REAL_DATA_URL = "../data/questions.json";
const SAMPLE_DATA_URL = "../data/questions.sample.json";

const el = (id) => document.getElementById(id);

let rawQuestions = [];
let quiz = [];       // shuffled + prepared questions for this run
let current = 0;
let results = [];    // {question, options, correctIndices, selected, isCorrect}
let answered = false;

// 실전 모드(Pearson VUE 스타일) 전용 상태
let examMode = false;
let userSelections = []; // userSelections[i] = 문제 i에서 선택한 옵션 인덱스 배열
let visited = [];         // visited[i] = 문제 i를 한 번이라도 본 적 있는지
let flagged = new Set();  // 검토 표시한 문제 인덱스
let examTimerId = null;
let remainingSeconds = null;
let englishPopupOpen = false; // "View in English" 팝업이 열려 있는지

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
    setStatus(`문제 ${rawQuestions.length}개를 불러왔습니다 (data/questions.json).`);
    return;
  } catch (e) {
    // data/questions.json이 없으면(아직 변환 전) 샘플로 폴백
  }
  try {
    rawQuestions = await tryFetch(SAMPLE_DATA_URL);
    setStatus(`샘플 문제 ${rawQuestions.length}개를 불러왔습니다. 앱(또는 run_local.bat/.sh)으로 실제 덤프를 변환하면 자동으로 그 문제가 로드됩니다.`);
  } catch (e) {
    setStatus("문제를 자동으로 불러오지 못했습니다 (file:// 로 열면 발생 가능). 아래 '고급: 다른 문제 파일 사용'에서 JSON 파일을 직접 선택해주세요.");
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

el("modeStudy").addEventListener("change", updateModeOptionsVisibility);
el("modeExam").addEventListener("change", updateModeOptionsVisibility);

function updateModeOptionsVisibility() {
  el("examOptions").classList.toggle("hidden", !el("modeExam").checked);
}

function buildQuiz() {
  if (!rawQuestions.length) {
    alert("불러온 문제가 없습니다.");
    return false;
  }
  const shuffleOpts = el("shuffleOptions").checked;
  const shuffleQuestionOrder = el("shuffleQuestions").checked;
  const countRaw = el("countInput").value;
  const count = countRaw ? Math.min(parseInt(countRaw, 10), rawQuestions.length) : rawQuestions.length;

  const ordered = shuffleQuestionOrder ? shuffle(rawQuestions) : rawQuestions;
  const pool = ordered.slice(0, count);

  quiz = pool.map((q) => {
    // question_en / options_en은 선택 항목(옵션)이다. parser가 영문 원문을
    // 함께 추출한 JSON에서만 존재하며, 없으면 "View in English"는 항상
    // 한국어를 보여준다.
    const indexed = q.options.map((text, idx) => ({
      text,
      textEn: q.options_en ? q.options_en[idx] : null,
      isCorrect: q.correct.includes(idx),
    }));
    const options = shuffleOpts ? shuffle(indexed) : indexed;
    return {
      id: q.id,
      question: q.question,
      questionEn: q.question_en || null,
      options,
      isMultiple: q.correct.length > 1,
    };
  });

  current = 0;
  results = [];
  answered = false;

  examMode = el("modeExam").checked;
  userSelections = quiz.map(() => []);
  visited = quiz.map(() => false);
  flagged = new Set();
  const minutesRaw = el("examMinutes").value;
  remainingSeconds = examMode && minutesRaw ? parseInt(minutesRaw, 10) * 60 : null;

  return true;
}

function showScreen(name) {
  ["setup", "quiz", "result"].forEach((s) => el(s).classList.toggle("hidden", s !== name));
  // 문제풀이 화면에서는 제목/설명 문구를 숨기고 문제 화면만 보이게 한다.
  el("pageHeader").classList.toggle("hidden", name === "quiz");
  // 제목 영역 폭을 현재 화면(패널)과 맞춰서 서로 어긋나 보이지 않게 한다.
  el("pageHeader").classList.toggle("wide", name === "result");
}

function applyModeChrome() {
  el("quiz").classList.toggle("exam-mode", examMode);
  el("studyBtnRow").classList.toggle("hidden", examMode);
  el("sectionReviewView").classList.add("hidden");
  el("sectionReviewBottombar").classList.add("hidden");
  el("examBottombar").classList.add("hidden");

  if (examMode) {
    // 실전 모드는 Pearson VUE처럼 문제 전에 안내(인트로) 화면을 먼저 보여준다.
    el("examTopbar").classList.remove("hidden");
    el("examTopbarRight").classList.add("hidden");
    el("examSubbar").classList.add("hidden");
    el("examBody").classList.add("hidden");
    el("examIntroBody").classList.remove("hidden");
    el("examIntroBottombar").classList.remove("hidden");
    el("examIntroTime").textContent =
      remainingSeconds != null
        ? `제한 시간: ${Math.round(remainingSeconds / 60)}분`
        : "제한 시간: 없음";
  } else {
    el("examTopbar").classList.add("hidden");
    el("examSubbar").classList.add("hidden");
    el("examIntroBody").classList.add("hidden");
    el("examIntroBottombar").classList.add("hidden");
    el("examBody").classList.remove("hidden");
  }
}

function enterExamQuestions() {
  el("examIntroBody").classList.add("hidden");
  el("examIntroBottombar").classList.add("hidden");
  el("examTopbarRight").classList.remove("hidden");
  el("examSubbar").classList.remove("hidden");
  el("examBody").classList.remove("hidden");
  el("examBottombar").classList.remove("hidden");
  renderQuestion();
  startTimerIfNeeded();
}

function renderQuestion() {
  answered = false;
  visited[current] = true;
  closeEnglishPopup();

  if (examMode) {
    el("progressWrap").classList.add("hidden");
  } else {
    el("progressWrap").classList.remove("hidden");
    el("progressText").textContent = `문제 ${current + 1} / ${quiz.length}`;
    const correctSoFar = results.filter((r) => r.isCorrect).length;
    el("scoreTally").textContent = results.length ? `정답 ${correctSoFar} / ${results.length}` : "";
    el("progressFill").style.width = `${Math.round((current / quiz.length) * 100)}%`;
  }

  renderQuestionBody();

  el("feedback").classList.add("hidden");
  el("feedback").textContent = "";

  if (examMode) {
    updateExamChrome();
  } else {
    el("submitBtn").classList.remove("hidden");
    el("submitBtn").disabled = false;
    el("nextBtn").classList.add("hidden");
  }
}

function renderQuestionBody() {
  const q = quiz[current];
  // 문제 원본(PDF)의 번호는 무시하고, 화면에 노출되는 순서(섞였으면 섞인
  // 순서) 그대로 1부터 매긴 번호를 문제 본문 앞에 붙인다.
  el("questionText").textContent = `${current + 1}. ${q.question}`;

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

    if (examMode) {
      input.checked = userSelections[current].includes(idx);
      input.addEventListener("change", () => {
        handleExamSelect(idx, input.checked, q.isMultiple);
        updateNavigatorIfOpen();
      });
      const letter = document.createElement("span");
      letter.className = "opt-letter";
      letter.textContent = String.fromCharCode(65 + idx) + ".";
      wrapper.appendChild(input);
      wrapper.appendChild(letter);
    } else {
      const badge = document.createElement("span");
      badge.className = "opt-badge";
      badge.textContent = String.fromCharCode(65 + idx);
      input.addEventListener("change", updateSelectedOptionStyles);
      wrapper.appendChild(input);
      wrapper.appendChild(badge);
    }

    const span = document.createElement("span");
    span.textContent = opt.text;
    wrapper.appendChild(span);
    list.appendChild(wrapper);
  });
}

// 학습 모드: 제출 전에도 지금 고른 보기가 시각적으로 강조되도록 한다.
function updateSelectedOptionStyles() {
  document.querySelectorAll("#optionsList .option").forEach((wrapper) => {
    const input = wrapper.querySelector("input");
    wrapper.classList.toggle("selected", input.checked);
  });
}

// "View in English" 버튼에 연결된 팝업 - 원문을 바꾸지 않고, 버튼 옆에 뜨는
// 작은 창에 영문 버전을 보여준다(실제 Pearson VUE 동작 방식).
function renderEnglishPopupContent() {
  const q = quiz[current];
  const qEl = el("englishPopupQuestion");
  const optsEl = el("englishPopupOptions");

  if (!q.questionEn) {
    qEl.innerHTML = '<span class="english-popup-empty">이 문제 세트에는 영문 원문이 없습니다.</span>';
    optsEl.innerHTML = "";
    return;
  }

  qEl.textContent = q.questionEn;
  optsEl.innerHTML = "";
  q.options.forEach((opt, idx) => {
    const row = document.createElement("div");
    row.className = "eo-option";
    const letter = String.fromCharCode(65 + idx);
    row.innerHTML = `<b>${letter}.</b> ${opt.textEn || "(영문 보기 없음)"}`;
    optsEl.appendChild(row);
  });
}

function openEnglishPopup() {
  renderEnglishPopupContent();
  englishPopupOpen = true;
  el("englishPopup").classList.remove("hidden");
}

function closeEnglishPopup() {
  englishPopupOpen = false;
  el("englishPopup").classList.add("hidden");
}

function toggleEnglishPopup() {
  if (englishPopupOpen) closeEnglishPopup();
  else openEnglishPopup();
}

function handleExamSelect(idx, checked, isMultiple) {
  if (isMultiple) {
    const set = new Set(userSelections[current]);
    if (checked) set.add(idx);
    else set.delete(idx);
    userSelections[current] = Array.from(set).sort((a, b) => a - b);
  } else {
    userSelections[current] = checked ? [idx] : [];
  }
}

function updateExamChrome() {
  el("examCounterText").textContent = `${current + 1} of ${quiz.length}`;
  el("flagBtn").classList.toggle("active", flagged.has(current));
  el("prevBtn").classList.toggle("hidden", current === 0);
  el("examNextBtn").textContent = current === quiz.length - 1 ? "Review ✓" : "Next ▶";
}

function questionStatus(i) {
  if (!visited[i]) return { label: "Unseen", cls: "status-unseen" };
  if (userSelections[i].length > 0) return { label: "Complete", cls: "status-complete" };
  return { label: "Incomplete", cls: "status-incomplete" };
}

function renderNavigator() {
  const tbody = el("navigatorTbody");
  tbody.innerHTML = "";
  let complete = 0, incomplete = 0, unseen = 0;
  quiz.forEach((q, i) => {
    const status = questionStatus(i);
    if (status.label === "Complete") complete += 1;
    else if (status.label === "Incomplete") incomplete += 1;
    else unseen += 1;

    const tr = document.createElement("tr");
    if (i === current) tr.classList.add("current");
    tr.innerHTML = `<td>문제 ${i + 1}</td><td class="${status.cls}">${status.label}</td><td>${flagged.has(i) ? "🚩" : ""}</td>`;
    tr.addEventListener("click", () => {
      current = i;
      closeNavigator();
      renderQuestion();
    });
    tbody.appendChild(tr);
  });
  el("navigatorSummary").textContent = `${quiz.length}문제, 완료 ${complete}, 미완료 ${incomplete}, 안 봄 ${unseen}`;
}

function updateNavigatorIfOpen() {
  if (!el("navigatorModal").classList.contains("hidden")) renderNavigator();
}

function openNavigator() {
  renderNavigator();
  el("navigatorModal").classList.remove("hidden");
}

function closeNavigator() {
  el("navigatorModal").classList.add("hidden");
}

function showSectionReview(filter = "all") {
  closeEnglishPopup();
  el("examBody").classList.add("hidden");
  el("examBottombar").classList.add("hidden");
  el("sectionReviewView").classList.remove("hidden");
  el("sectionReviewBottombar").classList.remove("hidden");
  // Time Remaining은 Section Review 중에도 계속 보이고(실제 Pearson VUE와
  // 동일), 특정 문제 전용인 카운터/Flag만 숨긴다.
  el("examCounterWrap").classList.add("hidden");
  el("examSubbar").classList.add("hidden");
  renderReviewGrid(filter);
}

function exitSectionReview(targetIdx) {
  el("sectionReviewView").classList.add("hidden");
  el("sectionReviewBottombar").classList.add("hidden");
  el("examBody").classList.remove("hidden");
  el("examBottombar").classList.remove("hidden");
  el("examCounterWrap").classList.remove("hidden");
  el("examSubbar").classList.remove("hidden");
  current = targetIdx;
  renderQuestion();
}

function renderReviewGrid(filter) {
  let complete = 0, incomplete = 0;
  const rows = quiz.map((q, i) => ({ i, status: questionStatus(i) }));
  rows.forEach((r) => {
    if (r.status.label === "Complete") complete += 1;
    else incomplete += 1;
  });

  const filtered = rows.filter((r) => {
    if (filter === "incomplete") return r.status.label !== "Complete";
    if (filter === "flagged") return flagged.has(r.i);
    return true;
  });

  el("sectionReviewSummary").textContent = `(${quiz.length} Questions, ${incomplete} Incomplete)`;

  const grid = el("sectionReviewGrid");
  grid.innerHTML = "";
  filtered.forEach((r) => {
    const cell = document.createElement("div");
    cell.className = "review-cell" + (flagged.has(r.i) ? " is-flagged" : "");
    cell.innerHTML = `
      <span class="review-flag">${flagged.has(r.i) ? "🚩" : ""}</span>
      <span class="review-qnum">Question ${r.i + 1}</span>
      <span class="review-status ${r.status.cls}">${r.status.label}</span>
    `;
    cell.addEventListener("click", () => exitSectionReview(r.i));
    grid.appendChild(cell);
  });

  if (!filtered.length) {
    grid.innerHTML = '<div class="review-cell" style="cursor:default;">해당하는 문제가 없습니다.</div>';
  }
}

function formatTime(totalSeconds) {
  const s = Math.max(0, totalSeconds);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

function startTimerIfNeeded() {
  clearInterval(examTimerId);
  if (remainingSeconds == null) {
    el("examTimer").classList.add("hidden");
    return;
  }
  el("examTimer").classList.remove("hidden");
  el("timeRemaining").textContent = formatTime(remainingSeconds);
  examTimerId = setInterval(() => {
    remainingSeconds -= 1;
    el("timeRemaining").textContent = formatTime(remainingSeconds);
    if (remainingSeconds <= 0) {
      clearInterval(examTimerId);
      alert("제한 시간이 종료되어 지금까지 답한 내용으로 채점합니다.");
      finishExam();
    }
  }, 1000);
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
    wrapper.classList.remove("selected");
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

function finishExam() {
  clearInterval(examTimerId);
  results = quiz.map((q, i) => {
    const correctIndices = q.options
      .map((o, idx) => (o.isCorrect ? idx : -1))
      .filter((idx) => idx !== -1);
    const selected = userSelections[i];
    const isCorrect =
      selected.length === correctIndices.length &&
      selected.every((s) => correctIndices.includes(s));
    return { question: q.question, options: q.options, correctIndices, selected, isCorrect };
  });
  showResult();
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
    const selectedText = r.selected.length ? r.selected.map((idx) => r.options[idx].text).join(" / ") : "(응답 없음)";
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
    applyModeChrome();
    if (!examMode) renderQuestion();
    // 실전 모드는 인트로 화면에서 examIntroNextBtn을 눌러야 문제가 시작된다.
  }
});
el("examIntroNextBtn").addEventListener("click", enterExamQuestions);
el("endExamIntroBtn").addEventListener("click", () => {
  clearInterval(examTimerId);
  showScreen("setup");
});
el("submitBtn").addEventListener("click", submitAnswer);
el("nextBtn").addEventListener("click", nextQuestion);
el("restartBtn").addEventListener("click", () => {
  clearInterval(examTimerId);
  showScreen("setup");
});

el("prevBtn").addEventListener("click", () => {
  if (current > 0) {
    current -= 1;
    renderQuestion();
  }
});
el("examNextBtn").addEventListener("click", () => {
  if (current < quiz.length - 1) {
    current += 1;
    renderQuestion();
  } else {
    showSectionReview("all");
  }
});
el("endReviewBtn").addEventListener("click", finishExam);
el("reviewAllBtn").addEventListener("click", () => renderReviewGrid("all"));
el("reviewIncompleteBtn").addEventListener("click", () => renderReviewGrid("incomplete"));
el("reviewFlaggedBtn").addEventListener("click", () => renderReviewGrid("flagged"));
el("flagBtn").addEventListener("click", () => {
  if (flagged.has(current)) flagged.delete(current);
  else flagged.add(current);
  updateExamChrome();
});
el("viewEnglishBtn").addEventListener("click", toggleEnglishPopup);
el("englishPopupClose").addEventListener("click", closeEnglishPopup);
el("navigatorBtn").addEventListener("click", openNavigator);
el("navigatorCloseBtn").addEventListener("click", closeNavigator);
el("navigatorCloseX").addEventListener("click", closeNavigator);
el("helpBtn").addEventListener("click", () => {
  alert(
    "보기를 선택한 뒤 Next로 다음 문제로 이동하세요.\n" +
      "Flag for Review로 나중에 다시 볼 문제를 표시할 수 있습니다.\n" +
      "Navigator에서 전체 문제 목록과 완료 상태를 보고 원하는 문제로 바로 이동할 수 있습니다.\n" +
      "마지막 문제에서 Review를 누르면 Section Review 화면이 나오고, End Review를 눌러야 최종 채점됩니다."
  );
});

loadDefault();

#!/usr/bin/env python3
"""
Convert an AWS exam-dump PDF into the JSON format used by the web quiz app.

Usage:
    python parse_pdf.py input.pdf -o ../data/questions.json

Works with the common "dump" PDF layout:

    QUESTION 1
    Some question text that can span
    multiple lines.

    A. Option one
    B. Option two
    C. Option three
    D. Option four

    Correct Answer: B

Also handles "NEW QUESTION 12", multi-line options, and multi-answer
questions ("Correct Answer: A C" / "Correct Answer: AC" / "Answer: A, C").

Community-corrected answers: examtopics 한글 덤프는 원래 정답이 틀린 것으로
밝혀지면 "정답:" 줄에 빨간색 글씨로 정정된 답을 덧붙이는 경우가 많다
(예: "정답: CE AE"에서 "AE"만 빨간색). 이 스크립트는 pdfplumber로 글자
색상을 읽어서, "정답"이 포함된 줄에 빨간색 글자가 있으면 그 글자들을
최종 정답으로 우선 사용한다. 빨간색 정정이 없으면 기존처럼 텍스트만으로
정답을 판별한다.

If your PDF uses a different layout, tweak the regexes below (QUESTION_RE,
OPTION_RE, ANSWER_RE) -- everything else (the web app) stays the same as
long as the output JSON keeps its shape.
"""
import argparse
import json
import re
import sys

QUESTION_LINE_RE = re.compile(
    r"^\s*(?:(?:NEW\s+)?QUESTION\s+(?P<qid_en>\d+)|질문\s*#?\s*(?P<qid_kr>\d+)\s*주제\s*\d+)\s*$",
    re.IGNORECASE,
)
OPTION_RE = re.compile(r"^\s*([A-F])[\.\)]\s+(.*)$")
ANSWER_RE = re.compile(r"^\s*(?:Correct\s+)?Answer\s*:\s*([A-F](?:\s*[,\s]\s*[A-F])*)\s*$", re.IGNORECASE)
# examtopics 한글 덤프는 "정답: D" 형식을 쓰고, 커뮤니티 투표로 정정된 답이
# 같은 줄 또는 다음 줄에 "정답: X" 형태로 한 번 더 나오기도 한다. 그 경우
# 마지막 "정답:" 값이 최종(정정된) 정답이므로 그 값을 우선한다. (색상 정보로
# 정정 여부를 판단할 수 없을 때의 최후 수단(fallback)으로만 쓰인다.)
KOREAN_ANSWER_LINE_RE = re.compile(r"^\s*정답\s*[:：]")
KOREAN_ANSWER_TOKEN_RE = re.compile(r"정답\s*[:：]?\s*([A-F](?:[,\s]*[A-F])*)")
ANSWER_LINE_TRIGGER_RE = re.compile(r"정답|\banswer\b", re.IGNORECASE)

RED_LETTERS = set("ABCDEF")


def _is_red(color):
    """examtopics 정정 표시는 빨간 계열(r 높고 g,b 낮음) 글자색을 쓴다."""
    if not color or not isinstance(color, (list, tuple)) or len(color) < 3:
        return False
    r, g, b = color[0], color[1], color[2]
    return r > 0.5 and (r - g) > 0.2 and (r - b) > 0.2


def extract_lines(pdf_path: str):
    """Return a list of (line_text, red_letters) tuples for the whole PDF.

    red_letters is a string of the A-F option letters on that line that are
    rendered in red (i.e. a community-corrected answer), in reading order.
    """
    import pdfplumber

    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for line in page.extract_text_lines():
                text = line["text"]
                red_letters = "".join(
                    ch["text"]
                    for ch in line["chars"]
                    if ch["text"] in RED_LETTERS and _is_red(ch.get("non_stroking_color"))
                )
                lines.append((text, red_letters))
    return lines


def split_into_blocks(lines):
    blocks = []
    current_qid = None
    current_lines = []
    for text, red in lines:
        m = QUESTION_LINE_RE.match(text)
        if m:
            if current_qid is not None:
                blocks.append((current_qid, current_lines))
            current_qid = m.group("qid_en") or m.group("qid_kr")
            current_lines = []
        elif current_qid is not None:
            current_lines.append((text, red))
    if current_qid is not None:
        blocks.append((current_qid, current_lines))
    return blocks


def parse_block(qid: str, block_lines):
    question_lines = []
    options = []  # list of (letter, text)
    answer_letters = []
    red_override = []
    current_option = None
    mode = "question"

    for raw_text, red in block_lines:
        line = raw_text.strip()
        if not line:
            continue

        if red and ANSWER_LINE_TRIGGER_RE.search(line):
            for ch in red:
                if ch not in red_override:
                    red_override.append(ch)

        ans_m = ANSWER_RE.match(line)
        if ans_m:
            if current_option is not None:
                options.append(current_option)
                current_option = None
            answer_letters = re.findall(r"[A-F]", ans_m.group(1).upper())
            mode = "answer"
            continue

        if KOREAN_ANSWER_LINE_RE.match(line):
            if current_option is not None:
                options.append(current_option)
                current_option = None
            tokens = KOREAN_ANSWER_TOKEN_RE.findall(line)
            if tokens:
                # 같은 줄에 원본 답과 커뮤니티가 정정한 답이 함께 있는 경우,
                # 마지막 토큰이 최종 정답이므로 그 값으로 덮어쓴다.
                answer_letters = re.findall(r"[A-F]", tokens[-1].upper())
            mode = "answer"
            continue

        opt_m = OPTION_RE.match(line)
        if opt_m:
            if current_option is not None:
                options.append(current_option)
            current_option = [opt_m.group(1), opt_m.group(2)]
            mode = "options"
            continue

        if mode == "question":
            question_lines.append(line)
        elif mode == "options" and current_option is not None:
            current_option[1] += " " + line

    if current_option is not None:
        options.append(current_option)

    # 빨간색으로 정정된 정답이 있으면 텍스트 기반 파싱 결과보다 우선한다.
    if red_override:
        answer_letters = red_override

    if not question_lines or len(options) < 2 or not answer_letters:
        return None

    letter_to_index = {letter: idx for idx, (letter, _) in enumerate(options)}
    correct_indices = sorted({letter_to_index[l] for l in answer_letters if l in letter_to_index})
    if not correct_indices:
        return None

    return {
        "id": int(qid),
        "question": " ".join(question_lines).strip(),
        "options": [text.strip() for _, text in options],
        "correct": correct_indices,
    }


def parse_pdf(pdf_path: str):
    lines = extract_lines(pdf_path)
    blocks = split_into_blocks(lines)

    questions = []
    skipped = []
    for qid, block_lines in blocks:
        parsed = parse_block(qid, block_lines)
        if parsed:
            questions.append(parsed)
        else:
            skipped.append(qid)

    return questions, skipped


def merge_english(questions, questions_en):
    """같은 문제 번호(id)의 영문 덤프를 찾아 question_en / options_en로 붙인다.

    영문 PDF의 보기 순서가 한글판과 같다고 가정하고 인덱스로 매칭한다(같은
    출처를 번역만 한 덤프라면 보통 보기 순서가 동일하다). 보기 개수가 다르면
    그 문제는 매칭하지 않고 건너뛴다.

    Returns the number of questions that got an English match.
    """
    en_by_id = {q["id"]: q for q in questions_en}
    matched = 0
    for q in questions:
        en = en_by_id.get(q["id"])
        if not en or len(en["options"]) != len(q["options"]):
            continue
        q["question_en"] = en["question"]
        q["options_en"] = en["options"]
        matched += 1
    return matched


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", help="Path to the exam-dump PDF file")
    ap.add_argument("-o", "--output", default="../data/questions.json", help="Output JSON path")
    ap.add_argument(
        "--en-pdf",
        help="같은 시험의 영문 원본 PDF (선택). 문제 번호로 매칭해 question_en/options_en을 "
        "함께 저장하며, 웹앱의 'View in English' 팝업에 쓰인다.",
    )
    args = ap.parse_args()

    questions, skipped = parse_pdf(args.pdf)

    if not questions:
        print("No questions were parsed. The PDF layout likely differs from what "
              "QUESTION_RE / OPTION_RE / ANSWER_RE expect -- open parse_pdf.py and "
              "adjust those regexes to match your dump's format.", file=sys.stderr)
        sys.exit(1)

    if args.en_pdf:
        questions_en, skipped_en = parse_pdf(args.en_pdf)
        matched = merge_english(questions, questions_en)
        print(f"Merged English text for {matched}/{len(questions)} questions from {args.en_pdf}")
        if skipped_en:
            print(f"(영문 PDF에서도 {len(skipped_en)}개 문제를 인식하지 못했습니다: {', '.join(skipped_en)})")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print(f"Parsed {len(questions)} questions -> {args.output}")
    if skipped:
        print(f"Skipped {len(skipped)} question block(s) that didn't match the expected "
              f"format (question numbers: {', '.join(skipped)}). Check them manually.")


if __name__ == "__main__":
    main()

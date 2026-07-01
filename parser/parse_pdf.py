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

If your PDF uses a different layout, tweak the regexes below (QUESTION_RE,
OPTION_RE, ANSWER_RE) -- everything else (the web app) stays the same as
long as the output JSON keeps its shape.
"""
import argparse
import json
import re
import sys

QUESTION_RE = re.compile(
    r"^\s*(?:(?:NEW\s+)?QUESTION\s+(?P<qid_en>\d+)|질문\s*#?\s*(?P<qid_kr>\d+)\s*주제\s*\d+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
OPTION_RE = re.compile(r"^\s*([A-F])[\.\)]\s+(.*)$")
ANSWER_RE = re.compile(r"^\s*(?:Correct\s+)?Answer\s*:\s*([A-F](?:\s*[,\s]\s*[A-F])*)\s*$", re.IGNORECASE)
# examtopics 한글 덤프는 "정답: D" 형식을 쓰고, 커뮤니티 투표로 정정된 답이
# 같은 줄 또는 다음 줄에 "정답: X" 형태로 한 번 더 나오기도 한다. 그 경우
# 마지막 "정답:" 값이 최종(정정된) 정답이므로 그 값을 우선한다.
KOREAN_ANSWER_LINE_RE = re.compile(r"^\s*정답\s*[:：]")
KOREAN_ANSWER_TOKEN_RE = re.compile(r"정답\s*[:：]?\s*([A-F](?:[,\s]*[A-F])*)")


def extract_text(pdf_path: str) -> str:
    import pdfplumber

    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            chunks.append(text)
    return "\n".join(chunks)


def split_into_blocks(full_text: str):
    matches = list(QUESTION_RE.finditer(full_text))
    blocks = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        qid = m.group("qid_en") or m.group("qid_kr")
        blocks.append((qid, full_text[start:end]))
    return blocks


def parse_block(qid: str, block: str):
    lines = [l.rstrip() for l in block.split("\n")]

    question_lines = []
    options = []  # list of (letter, text)
    answer_letters = []
    current_option = None
    mode = "question"

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

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
    full_text = extract_text(pdf_path)
    blocks = split_into_blocks(full_text)

    questions = []
    skipped = []
    for qid, block in blocks:
        parsed = parse_block(qid, block)
        if parsed:
            questions.append(parsed)
        else:
            skipped.append(qid)

    return questions, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", help="Path to the exam-dump PDF file")
    ap.add_argument("-o", "--output", default="../data/questions.json", help="Output JSON path")
    args = ap.parse_args()

    questions, skipped = parse_pdf(args.pdf)

    if not questions:
        print("No questions were parsed. The PDF layout likely differs from what "
              "QUESTION_RE / OPTION_RE / ANSWER_RE expect -- open parse_pdf.py and "
              "adjust those regexes to match your dump's format.", file=sys.stderr)
        sys.exit(1)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print(f"Parsed {len(questions)} questions -> {args.output}")
    if skipped:
        print(f"Skipped {len(skipped)} question block(s) that didn't match the expected "
              f"format (question numbers: {', '.join(skipped)}). Check them manually.")


if __name__ == "__main__":
    main()

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

QUESTION_RE = re.compile(r"^\s*(?:NEW\s+)?QUESTION\s+(\d+)\s*$", re.IGNORECASE | re.MULTILINE)
OPTION_RE = re.compile(r"^\s*([A-F])[\.\)]\s+(.*)$")
ANSWER_RE = re.compile(r"^\s*(?:Correct\s+)?Answer\s*:\s*([A-F](?:\s*[,\s]\s*[A-F])*)\s*$", re.IGNORECASE)


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
        blocks.append((m.group(1), full_text[start:end]))
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
            letters = re.findall(r"[A-F]", ans_m.group(1).upper())
            answer_letters.extend(letters)
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

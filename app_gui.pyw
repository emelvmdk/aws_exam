#!/usr/bin/env pythonw
"""
app_gui.py를 콘솔 창 없이 실행하기 위한 얇은 래퍼.

Windows는 .pyw 확장자를 기본적으로 pythonw.exe(콘솔 없는 파이썬)에 연결하므로,
이 파일을 더블클릭하면 AWS문제풀이.exe와 똑같은 화면이 콘솔 창 없이 뜬다.
PyInstaller로 빌드한 .exe가 Windows 스마트 앱 컨트롤(Smart App Control)에
막힐 때의 대안이다 - python.exe/pythonw.exe는 이미 신뢰된 실행 파일이라
막히지 않는다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app_gui

if __name__ == "__main__":
    app_gui.main()

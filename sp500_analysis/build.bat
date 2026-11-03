@echo off
chcp 65001 > nul
cd /d "%~dp0"

rem 배포 버전: version_info.txt의 버전과 함께 바꾼다
set VERSION=1.0.0
set PKG=release\SP500Analyzer_v%VERSION%

echo [1/4] 필요한 패키지 설치
python -m pip install -r requirements.txt || goto :error

echo [2/4] 아이콘 생성
if not exist app.ico python make_icon.py || goto :error

echo [3/4] 실행파일 빌드
rem --onefile        : 실행파일 하나로 묶기
rem --windowed       : 실행 시 검은 콘솔 창을 띄우지 않음
rem --add-data       : 창 아이콘으로 쓸 app.ico를 실행파일 안에 포함
rem --version-file   : 탐색기 속성 > 자세히에 표시할 제품명/버전
rem --exclude-module : pandas/matplotlib가 선택적으로 import하는 패키지 제외
rem                    (다른 Qt 바인딩이 함께 설치돼 있으면 빌드가 중단되고, 나머지는 용량만 커짐)
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name SP500Analyzer ^
    --icon app.ico ^
    --add-data "app.ico;." ^
    --version-file version_info.txt ^
    --exclude-module tkinter ^
    --exclude-module PySide6 --exclude-module PySide2 --exclude-module PyQt5 ^
    --exclude-module scipy --exclude-module IPython --exclude-module jedi ^
    --exclude-module zmq --exclude-module pygame ^
    sp500_gui.py || goto :error

echo [4/4] 배포용 압축파일 만들기
rem release\SP500Analyzer_v버전\ 폴더에 exe + 사용설명서를 모은 뒤 zip으로 묶는다
if exist "%PKG%" rmdir /s /q "%PKG%"
mkdir "%PKG%" || goto :error
copy /y dist\SP500Analyzer.exe "%PKG%\" > nul || goto :error
copy /y 사용설명서.txt "%PKG%\" > nul || goto :error
powershell -NoProfile -Command "Compress-Archive -Path '%PKG%' -DestinationPath '%PKG%.zip' -Force" || goto :error

echo.
echo 빌드 완료: dist\SP500Analyzer.exe
echo 배포 파일: %PKG%.zip
exit /b 0

:error
echo.
echo 빌드 실패
exit /b 1

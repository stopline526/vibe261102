@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo [1/3] 필요한 패키지 설치
python -m pip install -r requirements.txt || goto :error

echo [2/3] 아이콘 생성
if not exist app.ico python make_icon.py || goto :error

echo [3/3] 실행파일 빌드
rem --onefile   : 실행파일 하나로 묶기
rem --windowed  : 실행 시 검은 콘솔 창을 띄우지 않음
rem --add-data  : 창 아이콘으로 쓸 app.ico를 실행파일 안에 포함
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name KOSPI200Crawler ^
    --icon app.ico ^
    --add-data "app.ico;." ^
    kospi200_gui.py || goto :error

echo.
echo 빌드 완료: dist\KOSPI200Crawler.exe
exit /b 0

:error
echo.
echo 빌드 실패
exit /b 1

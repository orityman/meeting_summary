#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import atexit
import tempfile
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication, QMessageBox

# API 키 설정을 가장 먼저 로드하여 import 순서 문제 방지
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("경고: OPENAI_API_KEY가 설정되지 않았습니다. .env 파일에 API 키를 설정해주세요.")
    print(".env.example 파일을 .env로 복사하고 API 키를 입력하세요.")

# 프록시 설정 제거 (이 부분이 오류의 원인일 수 있음)
if 'http_proxy' in os.environ:
    del os.environ['http_proxy']
if 'https_proxy' in os.environ:
    del os.environ['https_proxy']

# UI 모듈 가져오기
from ui.main_window import MainWindow

def check_environment():
    """환경 변수 및 필요한 디렉토리 확인"""
    # 결과 디렉토리 생성
    results_dir = os.path.join(os.getcwd(), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    # ffmpeg 확인
    ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg.exe")
    if not os.path.exists(ffmpeg_path):
        print("경고: ffmpeg.exe를 찾을 수 없습니다. 프로그램 실행에 필요합니다.")
        print("ffmpeg.exe를 프로그램 폴더에 복사하세요.")
        
        # GUI 알림 표시
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
            
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("ffmpeg 필요")
        msg.setText("ffmpeg.exe가 필요합니다!")
        msg.setInformativeText("오디오/비디오 파일 처리를 위해 ffmpeg.exe가 필요합니다.\n프로그램 폴더에 ffmpeg.exe를 복사해주세요.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

def cleanup_temp_files():
    """프로그램 종료 시 임시 파일 정리"""
    temp_dir = tempfile.gettempdir()
    try:
        for filename in os.listdir(temp_dir):
            if filename.startswith('tmp') and filename.endswith('.mp3'):
                filepath = os.path.join(temp_dir, filename)
                try:
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                        print(f"임시 파일 삭제: {filepath}")
                except Exception:
                    pass
    except Exception:
        pass

def main():
    """애플리케이션 메인 함수"""
    # 종료 시 임시 파일 정리 함수 등록
    atexit.register(cleanup_temp_files)
    
    # Qt 애플리케이션 생성
    app = QApplication(sys.argv)
    
    # 환경 확인
    check_environment()
    
    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()
    
    # 애플리케이션 실행
    exit_code = app.exec()
    
    # 종료 전 정리
    print("프로그램 종료 중...")
    
    # 시스템 종료
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 
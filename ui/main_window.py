import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QTabWidget,
    QProgressBar, QMessageBox, QRadioButton, QButtonGroup, QGroupBox,
    QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QColor

from ui.worker_thread import WorkerThread

# Whisper API 파일 크기 제한 (25MB)
MAX_FILE_SIZE_MB = 25

class MainWindow(QMainWindow):
    """애플리케이션의 메인 창"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("LocalMeetingSummarizer - 로컬 회의 요약 프로그램")
        self.setMinimumSize(1000, 700)
        
        # 중앙 위젯 설정
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 메인 레이아웃 설정
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 상단 영역 (파일 선택, 옵션 등)
        self.setup_top_area()
        
        # 타이틀 추가
        self.add_title()
        
        # 중앙 분할 영역 설정 (진행 상황 및 결과 표시)
        self.setup_content_area()
        
        # 하단 영역 (버튼 등)
        self.setup_bottom_area()
        
        # 초기 상태 설정
        self.selected_file_path = None
        self.transcription_result = None
        self.paragraph_summary = None
        self.timestamped_summary = None
        self.worker = None
        
        # ffmpeg 확인
        self.has_ffmpeg = self.check_ffmpeg()
        
        # UI 초기화
        self.update_ui_state()
    
    def check_ffmpeg(self):
        """ffmpeg 존재 확인"""
        ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg.exe")
        has_ffmpeg = os.path.exists(ffmpeg_path)
        
        if not has_ffmpeg:
            # ffmpeg가 없으면 경고 라벨 추가
            self.ffmpeg_warning = QLabel("⚠️ ffmpeg.exe가 없습니다! 프로그램 폴더에 ffmpeg.exe를 복사하세요.")
            self.ffmpeg_warning.setStyleSheet("color: red; font-weight: bold; background-color: #FFEEEE; padding: 5px;")
            self.ffmpeg_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.main_layout.insertWidget(0, self.ffmpeg_warning)  # 최상단에 삽입
            
            # 로그에 경고 추가
            self.log_text.append("경고: ffmpeg.exe를 찾을 수 없습니다. 오디오/비디오 파일 처리를 위해 필요합니다.")
            self.log_text.append("ffmpeg.exe를 프로그램 폴더에 복사한 후 프로그램을 다시 시작하세요.")
        
        return has_ffmpeg
    
    def add_title(self):
        """애플리케이션 타이틀 추가"""
        title_label = QLabel("LocalMeetingSummarizer")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.main_layout.addWidget(title_label)
        
        subtitle_label = QLabel("로컬 환경에서 회의 녹음을 전사하고 요약하는 프로그램")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setFont(QFont("Arial", 10))
        self.main_layout.addWidget(subtitle_label)
        
        # API 제한 정보 표시
        limits_label = QLabel(f"참고: OpenAI Whisper API 파일 크기 제한은 {MAX_FILE_SIZE_MB}MB입니다. 더 큰 파일은 자동으로 압축됩니다.")
        limits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        limits_label.setStyleSheet("color: #666666; font-size: 10px;")
        self.main_layout.addWidget(limits_label)
        
        # 구분선 추가
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.main_layout.addWidget(line)
    
    def setup_top_area(self):
        """상단 영역 (파일 선택, 요약 옵션) 설정"""
        top_layout = QHBoxLayout()
        
        # 파일 선택 영역
        file_group = QGroupBox("1. 파일 선택")
        file_layout = QVBoxLayout(file_group)
        
        file_selector_layout = QHBoxLayout()
        self.file_path_label = QLabel("선택된 파일 없음")
        self.file_path_label.setWordWrap(True)
        
        select_file_button = QPushButton("파일 선택...")
        select_file_button.clicked.connect(self.select_file)
        select_file_button.setMinimumWidth(100)
        
        file_selector_layout.addWidget(self.file_path_label)
        file_selector_layout.addWidget(select_file_button)
        
        self.file_size_label = QLabel("")
        self.file_size_label.setStyleSheet("color: #666666; font-size: 10px;")
        
        file_layout.addLayout(file_selector_layout)
        file_layout.addWidget(self.file_size_label)
        
        # 요약 옵션 영역
        summary_group = QGroupBox("2. 요약 옵션")
        summary_layout = QVBoxLayout(summary_group)
        
        # 요약 옵션 레이블 변경
        self.paragraph_option = QRadioButton("상세 요약 (AI 비서 스타일)")
        self.timestamped_option = QRadioButton("타임스탬프 요약 (AI 비서 스타일)")
        self.both_option = QRadioButton("두 가지 요약 모두 생성")
        
        self.paragraph_option.setChecked(True)  # 기본값 설정
        
        summary_layout.addWidget(self.paragraph_option)
        summary_layout.addWidget(self.timestamped_option)
        summary_layout.addWidget(self.both_option)
        
        # 모델 정보 레이블 추가
        model_info_label = QLabel("사용 모델: OpenAI o3-mini")
        model_info_label.setStyleSheet("color: #666666; font-size: 10px;")
        summary_layout.addWidget(model_info_label)
        
        # 상단 레이아웃에 위젯 추가
        top_layout.addWidget(file_group, 2)
        top_layout.addWidget(summary_group, 1)
        
        self.main_layout.addLayout(top_layout)
    
    def setup_content_area(self):
        """중앙 콘텐츠 영역 (탭 및 결과 표시) 설정"""
        self.tabs = QTabWidget()
        
        # 탭 1: 진행 상태 및 로그
        self.progress_tab = QWidget()
        progress_layout = QVBoxLayout(self.progress_tab)
        
        self.status_label = QLabel("파일을 선택하고 '전사 및 요약 시작' 버튼을 클릭하세요.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(QLabel("로그:"))
        progress_layout.addWidget(self.log_text)
        
        # 탭 2: 전사 결과
        self.transcription_tab = QWidget()
        transcription_layout = QVBoxLayout(self.transcription_tab)
        
        self.transcription_text = QTextEdit()
        self.transcription_text.setReadOnly(True)
        
        transcription_layout.addWidget(QLabel("전사 결과:"))
        transcription_layout.addWidget(self.transcription_text)
        
        # 탭 3: 요약 결과
        self.summary_tab = QWidget()
        summary_layout = QVBoxLayout(self.summary_tab)
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        
        summary_layout.addWidget(QLabel("요약 결과:"))
        summary_layout.addWidget(self.summary_text)
        
        # 탭 추가
        self.tabs.addTab(self.progress_tab, "진행 상태")
        self.tabs.addTab(self.transcription_tab, "전사 결과")
        self.tabs.addTab(self.summary_tab, "요약 결과")
        
        self.main_layout.addWidget(self.tabs, 1)
    
    def setup_bottom_area(self):
        """하단 영역 (버튼) 설정"""
        bottom_layout = QHBoxLayout()
        
        # 전사 및 요약 시작 버튼
        self.start_button = QPushButton("전사 및 요약 시작")
        self.start_button.clicked.connect(self.start_processing)
        self.start_button.setEnabled(False)
        self.start_button.setMinimumHeight(40)
        
        # 저장 버튼
        self.save_button = QPushButton("결과 저장")
        self.save_button.clicked.connect(self.save_results)
        self.save_button.setEnabled(False)
        self.save_button.setMinimumHeight(40)
        
        # 초기화 버튼
        self.reset_button = QPushButton("초기화")
        self.reset_button.clicked.connect(self.reset_ui)
        self.reset_button.setMinimumHeight(40)
        
        bottom_layout.addWidget(self.start_button)
        bottom_layout.addWidget(self.save_button)
        bottom_layout.addWidget(self.reset_button)
        
        self.main_layout.addLayout(bottom_layout)
    
    def select_file(self):
        """파일 선택 다이얼로그 표시"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self,
            "오디오/비디오 파일 선택",
            "",
            "미디어 파일 (*.mp3 *.mp4 *.wav *.m4a *.avi *.mov);;모든 파일 (*.*)"
        )
        
        if file_path:
            self.selected_file_path = file_path
            file_name = os.path.basename(file_path)
            self.file_path_label.setText(file_name)
            
            # 파일 크기 표시
            file_size_bytes = os.path.getsize(file_path)
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            size_text = f"파일 크기: {file_size_mb:.2f}MB"
            if file_size_mb > MAX_FILE_SIZE_MB:
                size_text += f" (API 제한 {MAX_FILE_SIZE_MB}MB 초과, 자동 압축됨)"
                self.file_size_label.setStyleSheet("color: #FF6600; font-size: 10px;")
            else:
                self.file_size_label.setStyleSheet("color: #007700; font-size: 10px;")
                
            self.file_size_label.setText(size_text)
            
            self.update_ui_state()
            self.log_text.append(f"파일이 선택되었습니다: {file_name}")
            self.log_text.append(f"파일 크기: {file_size_mb:.2f}MB")
            
            if file_size_mb > MAX_FILE_SIZE_MB:
                self.log_text.append(f"주의: 파일 크기가 Whisper API 제한({MAX_FILE_SIZE_MB}MB)을 초과합니다.")
                self.log_text.append("처리 시 자동으로 파일이 압축되거나 일부만 처리될 수 있습니다.")
            
            # ffmpeg 확인
            if not self.has_ffmpeg:
                self.log_text.append("경고: ffmpeg.exe를 찾을 수 없습니다. 오디오 변환이 불가능합니다.")
                QMessageBox.warning(
                    self,
                    "ffmpeg 필요",
                    "ffmpeg.exe가 없습니다!\n오디오/비디오 파일 처리를 위해 필요합니다.\n프로그램 폴더에 ffmpeg.exe를 복사한 후 다시 시작하세요."
                )
    
    def start_processing(self):
        """전사 및 요약 처리 시작"""
        if not self.selected_file_path:
            QMessageBox.warning(self, "경고", "먼저 파일을 선택해주세요.")
            return
        
        if not self.has_ffmpeg:
            QMessageBox.critical(
                self,
                "ffmpeg 필요",
                "ffmpeg.exe가 없어 처리할 수 없습니다!\n프로그램 폴더에 ffmpeg.exe를 복사한 후 다시 시작하세요."
            )
            return
        
        # 파일 크기 확인
        file_size_bytes = os.path.getsize(self.selected_file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        if file_size_mb > MAX_FILE_SIZE_MB * 1.5:  # 37.5MB 이상이면 경고
            reply = QMessageBox.question(
                self,
                "큰 파일 경고",
                f"파일 크기가 {file_size_mb:.1f}MB로 매우 큽니다.\n"
                f"OpenAI API 제한({MAX_FILE_SIZE_MB}MB)을 크게 초과하므로 파일이 크게 압축되거나 앞부분만 처리될 수 있습니다.\n"
                "계속 진행하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
        
        # 요약 옵션 확인
        summary_types = []
        if self.paragraph_option.isChecked() or self.both_option.isChecked():
            summary_types.append("paragraph")
        if self.timestamped_option.isChecked() or self.both_option.isChecked():
            summary_types.append("timestamped")
        
        # UI 상태 업데이트
        self.start_button.setEnabled(False)
        self.status_label.setText("처리 중...")
        self.progress_bar.setValue(10)
        self.log_text.append("전사 및 요약 작업을 시작합니다...")
        
        # 작업 스레드 생성 및 시작
        self.worker = WorkerThread(self.selected_file_path, summary_types)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.log_update.connect(self.log_text.append)
        self.worker.start()
    
    def on_processing_finished(self, results):
        """처리 완료 후 호출되는 메서드"""
        if results.get("success", False):
            self.transcription_result = results.get("transcription", "")
            self.paragraph_summary = results.get("paragraph_summary", "")
            self.timestamped_summary = results.get("timestamped_summary", "")
            
            # UI 업데이트
            self.transcription_text.setText(self.transcription_result)
            
            # 요약 텍스트 설정
            summary_text = ""
            if self.paragraph_summary:
                summary_text += "## 문단별 요약\n\n" + self.paragraph_summary + "\n\n"
            if self.timestamped_summary:
                summary_text += "## 시간대별 요약\n\n" + self.timestamped_summary
            
            self.summary_text.setText(summary_text)
            
            # 탭 전환
            self.tabs.setCurrentIndex(2)  # 요약 결과 탭으로 전환
            
            # 상태 업데이트
            self.status_label.setText("처리 완료!")
            self.progress_bar.setValue(100)
            self.log_text.append("전사 및 요약이 성공적으로 완료되었습니다.")
            
            # 저장 버튼 활성화
            self.save_button.setEnabled(True)
        else:
            error_msg = results.get("error", "알 수 없는 오류가 발생했습니다.")
            QMessageBox.critical(self, "오류", f"처리 중 오류가 발생했습니다: {error_msg}")
            self.status_label.setText("오류 발생")
            self.progress_bar.setValue(0)
            self.log_text.append(f"오류: {error_msg}")
        
        # 시작 버튼 재활성화
        self.start_button.setEnabled(True)
        
        # 작업자 스레드 정리
        self.worker = None
    
    def update_progress(self, progress, status):
        """진행 상황 업데이트"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)
    
    def save_results(self):
        """결과 저장"""
        if not (self.transcription_result or self.paragraph_summary or self.timestamped_summary):
            QMessageBox.warning(self, "경고", "저장할 결과가 없습니다.")
            return
        
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(
            self,
            "결과 저장",
            "",
            "텍스트 파일 (*.txt);;모든 파일 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("# 회의 요약 결과\n\n")
                    
                    if self.paragraph_summary:
                        f.write("## 1. 요약 (문단별)\n")
                        f.write(self.paragraph_summary)
                        f.write("\n\n")
                    
                    if self.timestamped_summary:
                        f.write("## 2. 요약 (시간대별)\n")
                        f.write(self.timestamped_summary)
                        f.write("\n\n")
                    
                    if self.transcription_result:
                        f.write("## 3. 전체 전사 내용\n")
                        f.write(self.transcription_result)
                
                self.log_text.append(f"결과가 저장되었습니다: {file_path}")
                QMessageBox.information(self, "저장 완료", f"결과가 성공적으로 저장되었습니다:\n{file_path}")
            
            except Exception as e:
                QMessageBox.critical(self, "저장 오류", f"결과 저장 중 오류가 발생했습니다: {str(e)}")
                self.log_text.append(f"저장 오류: {str(e)}")
    
    def reset_ui(self):
        """UI 초기화"""
        # 작업 스레드가 실행 중이면 중지
        if self.worker and self.worker.isRunning():
            self.log_text.append("작업 중지 중...")
            self.worker.stop()
            # 이제 worker.stop()이 작업이 완료될 때까지 기다리므로 별도로 wait() 호출 불필요
            self.worker = None
            self.log_text.append("작업이 중지되었습니다.")
        
        self.selected_file_path = None
        self.transcription_result = None
        self.paragraph_summary = None
        self.timestamped_summary = None
        
        # UI 컴포넌트 초기화
        self.file_path_label.setText("선택된 파일 없음")
        self.file_size_label.setText("")
        self.paragraph_option.setChecked(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("파일을 선택하고 '전사 및 요약 시작' 버튼을 클릭하세요.")
        self.transcription_text.clear()
        self.summary_text.clear()
        self.log_text.clear()
        
        # 버튼 상태 업데이트
        self.update_ui_state()
        
        self.tabs.setCurrentIndex(0)  # 진행 상태 탭으로 전환
    
    def update_ui_state(self):
        """UI 상태 업데이트"""
        # 시작 버튼 활성화 여부 결정 (파일 선택 여부 + ffmpeg 존재 여부)
        self.start_button.setEnabled(self.selected_file_path is not None and self.has_ffmpeg)
        
        # 저장 버튼 활성화 여부 결정
        has_results = (self.transcription_result is not None or 
                      self.paragraph_summary is not None or 
                      self.timestamped_summary is not None)
        self.save_button.setEnabled(has_results)
    
    def closeEvent(self, event):
        """창 닫기 이벤트 처리"""
        # 작업 스레드가 실행 중이면 중지
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, '확인',
                "작업이 진행 중입니다. 정말로 종료하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.log_text.append("프로그램 종료 중... 작업을 정리하는 중입니다.")
                # 진행 상태 탭으로 전환하여 사용자에게 종료 중임을 표시
                self.tabs.setCurrentIndex(0)
                
                # 애플리케이션이 종료되기 전에 모든 이벤트가 처리되도록 함
                QApplication.processEvents()
                
                # 스레드 종료 (stop 메서드가 정상적으로 스레드를 종료할 때까지 기다림)
                self.worker.stop()
                self.worker = None
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
import os
import tempfile
import traceback
from PyQt6.QtCore import QThread, pyqtSignal, QObject, QMutex, QMutexLocker

from utils.api import OpenAIAPI
from utils.audio import AudioProcessor
from utils.storage import Storage

class WorkerThread(QThread):
    """백그라운드에서 전사 및 요약 작업을 수행하는 작업자 스레드"""
    
    # 시그널 정의
    finished = pyqtSignal(dict)  # 작업 완료 시 결과를 전달하는 시그널
    progress_update = pyqtSignal(int, str)  # 진행 상황을 업데이트하는 시그널 (진행률, 상태 메시지)
    log_update = pyqtSignal(str)  # 로그 메시지를 업데이트하는 시그널
    
    def __init__(self, file_path, summary_types):
        """
        초기화
        
        Args:
            file_path (str): 오디오/비디오 파일 경로
            summary_types (list): 요약 유형 목록 ('paragraph', 'timestamped')
        """
        super().__init__()
        self.file_path = file_path
        self.summary_types = summary_types
        self.temp_files = []  # 임시 파일 목록 (정리를 위해)
        self.stopped = False  # 종료 요청 플래그
        self.mutex = QMutex()  # 스레드 동기화용 뮤텍스
        
        # 유틸리티 클래스 인스턴스 생성
        self.api = OpenAIAPI()
        self.audio_processor = AudioProcessor()
        self.storage = Storage()
    
    def run(self):
        """스레드 실행"""
        try:
            # 1. 진행 상황 업데이트: 오디오 처리 시작
            self.progress_update.emit(10, "오디오 파일 처리 중...")
            self.log_update.emit(f"파일 처리 중: {os.path.basename(self.file_path)}")
            
            # 파일 존재 확인
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {self.file_path}")
            
            self.log_update.emit(f"파일 크기: {os.path.getsize(self.file_path)} bytes")
            
            # 종료 요청 확인
            if self.check_stopped():
                return
            
            # 2. 오디오 파일 변환 (필요한 경우)
            self.log_update.emit("오디오 파일을 MP3 형식으로 변환 중...")
            
            try:
                processed_file = self.audio_processor.convert_to_mp3(self.file_path)
                self.log_update.emit(f"변환된 파일 경로: {processed_file}")
                self.temp_files.append(processed_file)
                self.log_update.emit("오디오 변환 완료")
            except Exception as e:
                error_msg = f"오디오 변환 중 오류 발생: {str(e)}"
                self.log_update.emit(error_msg)
                self.log_update.emit(traceback.format_exc())
                raise RuntimeError(error_msg)
            
            # 종료 요청 확인
            if self.check_stopped():
                return
            
            # 3. 진행 상황 업데이트: 전사 시작
            self.progress_update.emit(20, "Whisper API를 통해 전사 중...")
            self.log_update.emit("음성을 텍스트로 전사하는 중...")
            
            # 4. OpenAI Whisper API를 사용하여 전사
            try:
                transcription_response = self.api.transcribe_audio(processed_file)
                self.log_update.emit("전사 완료")
            except Exception as e:
                error_msg = f"전사 중 오류 발생: {str(e)}"
                self.log_update.emit(error_msg)
                self.log_update.emit(traceback.format_exc())
                raise RuntimeError(error_msg)
            
            # 종료 요청 확인
            if self.check_stopped():
                return
            
            # 5. 전사 결과 추출 및 처리
            if not transcription_response or not hasattr(transcription_response, 'text'):
                error_msg = "전사 응답이 유효하지 않습니다."
                self.log_update.emit(error_msg)
                raise RuntimeError(error_msg)
            
            full_text = transcription_response.text
            segments = getattr(transcription_response, 'segments', [])
            
            # 타임스탬프가 있는 전사 텍스트 생성
            timestamped_text = self._create_timestamped_text(segments)
            
            # 전사 결과 저장
            self.log_update.emit("전사 결과 저장 중...")
            self.storage.save_transcription(transcription_response)
            
            # 종료 요청 확인
            if self.check_stopped():
                return
            
            # 6. 진행 상황 업데이트: 요약 시작
            self.progress_update.emit(50, "ChatGPT API를 통해 요약 중...")
            
            # 7. 요약 결과 변수 초기화
            paragraph_summary = None
            timestamped_summary = None
            
            # 8. 요약 유형에 따라 처리
            if "paragraph" in self.summary_types:
                self.log_update.emit("문단별 요약 생성 중...")
                paragraph_summary = self.api.summarize_text(full_text, "paragraph")
                self.log_update.emit("문단별 요약 완료")
                self.progress_update.emit(70, "문단별 요약 완료")
            
            # 종료 요청 확인
            if self.check_stopped():
                return
            
            if "timestamped" in self.summary_types:
                self.log_update.emit("시간대별 요약 생성 중...")
                timestamped_summary = self.api.summarize_text(timestamped_text, "timestamped")
                self.log_update.emit("시간대별 요약 완료")
                self.progress_update.emit(90, "시간대별 요약 완료")
            
            # 종료 요청 확인
            if self.check_stopped():
                return
            
            # 9. 요약 결과 저장
            self.log_update.emit("요약 결과 저장 중...")
            if paragraph_summary:
                self.storage.save_summary(paragraph_summary, "paragraph")
            if timestamped_summary:
                self.storage.save_summary(timestamped_summary, "timestamped")
            
            # 모든 결과 통합 저장
            if paragraph_summary or timestamped_summary:
                self.storage.save_full_result(full_text, paragraph_summary or "", timestamped_summary or "")
            
            # 종료 요청 확인
            if self.check_stopped():
                return
            
            # 10. 완료 처리
            self.progress_update.emit(100, "처리 완료!")
            self.log_update.emit("전사 및 요약 작업이 완료되었습니다.")
            
            # 결과 전달
            results = {
                "success": True,
                "transcription": full_text,
                "paragraph_summary": paragraph_summary,
                "timestamped_summary": timestamped_summary
            }
            self.finished.emit(results)
        
        except Exception as e:
            # 오류 처리
            error_message = str(e)
            self.log_update.emit(f"오류 발생: {error_message}")
            
            # 자세한 오류 정보 출력
            self.log_update.emit(traceback.format_exc())
            
            self.finished.emit({"success": False, "error": error_message})
        
        finally:
            # 임시 파일 정리
            self._cleanup_temp_files()
    
    def _create_timestamped_text(self, segments):
        """
        타임스탬프가 있는 텍스트 생성
        
        Args:
            segments (list): 전사 세그먼트 목록
            
        Returns:
            str: 타임스탬프가 포함된 텍스트
        """
        if not segments:
            return "타임스탬프 정보가 없습니다."
        
        timestamped_text = ""
        for segment in segments:
            start_time = self.audio_processor.format_timestamp(segment.start * 1000)
            end_time = self.audio_processor.format_timestamp(segment.end * 1000)
            timestamped_text += f"[{start_time} - {end_time}] {segment.text}\n\n"
        
        return timestamped_text
    
    def _cleanup_temp_files(self):
        """임시 파일 정리"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    self.log_update.emit(f"임시 파일 삭제: {temp_file}")
            except Exception as e:
                self.log_update.emit(f"임시 파일 삭제 중 오류 발생: {str(e)}")
    
    def check_stopped(self):
        """종료 요청 확인"""
        with QMutexLocker(self.mutex):
            return self.stopped
    
    def stop(self):
        """스레드 중지 요청"""
        with QMutexLocker(self.mutex):
            self.stopped = True
        self.log_update.emit("작업 중지 요청됨")
        
        # 작업이 끝날 때까지 기다림
        if not self.wait(5000):  # 5초 대기
            self.log_update.emit("스레드 강제 종료")
            self.terminate()
            self.wait()  # 스레드가 종료될 때까지 기다림
        
        # 임시 파일 정리
        self._cleanup_temp_files()
    
    def __del__(self):
        """소멸자"""
        self.wait()  # 스레드가 종료될 때까지 기다림 
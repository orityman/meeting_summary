import os
import json
from datetime import datetime

class Storage:
    """로컬 파일 저장 및 관리를 위한 클래스"""
    
    def __init__(self, base_dir=None):
        """
        Storage 클래스 초기화
        
        Args:
            base_dir (str, optional): 결과를 저장할 기본 디렉토리. 기본값은 현재 디렉토리의 'results' 폴더.
        """
        if base_dir is None:
            # 기본 저장 디렉토리는 프로젝트 폴더 내의 'results' 디렉토리
            self.base_dir = os.path.join(os.getcwd(), 'results')
        else:
            self.base_dir = base_dir
        
        # 필요한 경우 디렉토리 생성
        os.makedirs(self.base_dir, exist_ok=True)
    
    def save_transcription(self, transcription_data, file_name=None):
        """
        전사 결과를 JSON 파일로 저장합니다.
        
        Args:
            transcription_data (dict 또는 TranscriptionResponse): 전사 데이터
            file_name (str, optional): 저장할 파일 이름. 기본값은 타임스탬프를 포함한 이름.
            
        Returns:
            str: 저장된 파일의 경로
        """
        if file_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"transcription_{timestamp}.json"
        
        file_path = os.path.join(self.base_dir, file_name)
        
        # TranscriptionResponse 객체를 딕셔너리로 변환
        if hasattr(transcription_data, '__dict__'):
            # 사용자 정의 객체인 경우
            data_dict = {
                "text": getattr(transcription_data, 'text', ''),
                "segments": []
            }
            
            # segments 처리 (있는 경우)
            segments = getattr(transcription_data, 'segments', [])
            for segment in segments:
                segment_dict = {
                    "start": getattr(segment, 'start', 0),
                    "end": getattr(segment, 'end', 0),
                    "text": getattr(segment, 'text', '')
                }
                data_dict["segments"].append(segment_dict)
        else:
            # 이미 딕셔너리인 경우
            data_dict = transcription_data
        
        # JSON으로 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=2)
        
        return file_path
    
    def save_summary(self, summary_text, summary_type="paragraph", file_name=None):
        """
        요약 결과를 텍스트 파일로 저장합니다.
        
        Args:
            summary_text (str): 요약 텍스트
            summary_type (str): 요약 유형 ('paragraph' 또는 'timestamped')
            file_name (str, optional): 저장할 파일 이름. 기본값은 타임스탬프를 포함한 이름.
            
        Returns:
            str: 저장된 파일의 경로
        """
        if file_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"summary_{summary_type}_{timestamp}.txt"
        
        file_path = os.path.join(self.base_dir, file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(summary_text)
        
        return file_path
    
    def save_full_result(self, transcription_text, paragraph_summary, timestamped_summary=None, file_name=None):
        """
        전사 및 모든 요약 결과를 하나의 텍스트 파일로 저장합니다.
        
        Args:
            transcription_text (str): 전사 텍스트
            paragraph_summary (str): 문단 요약 텍스트
            timestamped_summary (str, optional): 시간대별 요약 텍스트
            file_name (str, optional): 저장할 파일 이름. 기본값은 타임스탬프를 포함한 이름.
            
        Returns:
            str: 저장된 파일의 경로
        """
        if file_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"meeting_summary_{timestamp}.txt"
        
        file_path = os.path.join(self.base_dir, file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# 회의 요약 결과\n\n")
            
            if paragraph_summary:
                f.write("## 1. 요약 (문단별)\n")
                f.write(paragraph_summary)
                f.write("\n\n")
            
            if timestamped_summary:
                f.write("## 2. 요약 (시간대별)\n")
                f.write(timestamped_summary)
                f.write("\n\n")
            
            if transcription_text:
                f.write("## 3. 전체 전사 내용\n")
                f.write(transcription_text)
        
        return file_path 
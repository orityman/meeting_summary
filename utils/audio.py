import os
from pydub import AudioSegment
import tempfile
import sys
import subprocess

# 프로젝트 경로 내의 ffmpeg.exe 파일 경로 설정
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ffmpeg_path = os.path.join(current_dir, "ffmpeg.exe")
ffprobe_path = os.path.join(current_dir, "ffprobe.exe")

# Whisper API 파일 크기 제한 (25MB = 26,214,400 바이트)
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB in bytes

# ffmpeg.exe가 존재하는지 확인하고 경로 설정
if os.path.exists(ffmpeg_path):
    AudioSegment.converter = ffmpeg_path
    print(f"ffmpeg.exe 경로 설정: {ffmpeg_path}")
    
# ffprobe.exe가 존재하는지 확인하고 경로 설정
if os.path.exists(ffprobe_path):
    AudioSegment.ffprobe = ffprobe_path
    print(f"ffprobe.exe 경로 설정: {ffprobe_path}")
elif os.path.exists(ffmpeg_path):
    # ffprobe.exe가 없지만 ffmpeg.exe가 있는 경우, ffmpeg.exe를 ffprobe.exe로도 사용
    AudioSegment.ffprobe = ffmpeg_path
    print(f"ffprobe.exe가 없어 ffmpeg.exe를 사용: {ffmpeg_path}")

class AudioProcessor:
    """오디오 파일 처리를 위한 클래스"""
    
    @staticmethod
    def convert_to_mp3(input_file_path):
        """
        다양한 오디오/비디오 파일 형식을 MP3로 변환합니다.
        
        Args:
            input_file_path (str): 입력 파일 경로
            
        Returns:
            str: 변환된 MP3 파일의 경로 (API 제한에 맞게 처리됨)
        """
        try:
            file_name = os.path.basename(input_file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # 임시 파일 생성
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_file_path = temp_file.name
            temp_file.close()
            
            # 파일 확장자에 따라 다르게 처리
            if file_ext in ['.mp3']:
                # 이미 MP3 파일인 경우 복사만 수행
                audio = AudioSegment.from_mp3(input_file_path)
            elif file_ext in ['.wav']:
                audio = AudioSegment.from_wav(input_file_path)
            elif file_ext in ['.mp4', '.avi', '.mov']:
                # 비디오 파일에서 오디오 추출
                audio = AudioSegment.from_file(input_file_path)
            else:
                # 기타 형식
                try:
                    audio = AudioSegment.from_file(input_file_path)
                except Exception as e:
                    raise ValueError(f"지원하지 않는 파일 형식입니다: {file_ext}, 오류: {e}")
            
            # 스테레오를 모노로 변환하여 파일 크기 줄이기
            audio = audio.set_channels(1)
            
            # 필요한 경우 비트레이트 조정
            file_size = len(audio.raw_data)
            print(f"변환 전 오디오 크기: {file_size} bytes")
            
            # 파일 크기가 API 제한을 초과하는 경우
            if file_size > MAX_FILE_SIZE:
                print(f"파일 크기가 API 제한(25MB)을 초과합니다. 오디오 품질을 조정합니다.")
                
                # 64Kbps 비트레이트로 압축하여 파일 크기 줄이기
                bitrate = "64k"
                audio.export(temp_file_path, format="mp3", bitrate=bitrate)
                
                # 압축 후에도 파일 크기가 크면 샘플링 레이트도 줄이기
                if os.path.getsize(temp_file_path) > MAX_FILE_SIZE:
                    print("추가 압축이 필요합니다. 샘플링 레이트를 낮춥니다.")
                    audio = audio.set_frame_rate(16000)  # 16kHz로 설정
                    audio.export(temp_file_path, format="mp3", bitrate=bitrate)
                
                # 그래도 크면 오디오 길이 앞부분만 사용 (25MB 이내로)
                if os.path.getsize(temp_file_path) > MAX_FILE_SIZE:
                    print("파일이 여전히 큽니다. 앞부분 25MB만 처리합니다.")
                    # 25MB 이내로 들어갈 때까지 오디오 길이 계산
                    original_duration = len(audio)
                    new_duration = int(original_duration * (MAX_FILE_SIZE / os.path.getsize(temp_file_path)) * 0.95)  # 95% 정도만 사용
                    
                    # 앞부분만 잘라내기
                    audio = audio[:new_duration]
                    audio.export(temp_file_path, format="mp3", bitrate=bitrate)
                    
                    print(f"전체 오디오 길이: {original_duration}ms, 처리할 길이: {new_duration}ms")
                    print("주의: 파일이 너무 커서 일부만 처리됩니다. 더 정확한 전사를 원하시면 파일을 여러 개로 나누어 처리하세요.")
            else:
                # 파일 크기가 적당하면 그대로 내보내기
                audio.export(temp_file_path, format="mp3")
            
            print(f"변환 후 파일 크기: {os.path.getsize(temp_file_path)} bytes")
            return temp_file_path
        
        except Exception as e:
            print(f"오디오 변환 중 오류 발생: {e}")
            raise
    
    @staticmethod
    def format_timestamp(milliseconds):
        """
        밀리초를 HH:MM:SS 형식으로 변환합니다.
        
        Args:
            milliseconds (float): 밀리초 단위의 시간
            
        Returns:
            str: HH:MM:SS 형식의 시간 문자열
        """
        seconds = int(milliseconds / 1000)
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" 
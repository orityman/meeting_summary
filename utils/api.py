import os
import openai
from dotenv import load_dotenv

# .env 파일에서 API 키 로드
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# OpenAI API 키 설정
openai.api_key = api_key
print("OpenAI API 키 설정 완료")

class OpenAIAPI:
    """OpenAI API와의 통신을 관리하는 클래스"""
    
    @staticmethod
    def transcribe_audio(audio_file_path):
        """
        Whisper API를 사용하여 오디오 파일을 텍스트로 변환합니다.
        
        Args:
            audio_file_path (str): 오디오 파일의 경로
            
        Returns:
            dict: 전사 결과 (텍스트 및 타임스탬프 포함)
        """
        try:
            print(f"오디오 파일 전사 시작: {audio_file_path}")
            print(f"파일 크기: {os.path.getsize(audio_file_path)} bytes")
            print(f"파일 존재 여부: {os.path.exists(audio_file_path)}")
            
            with open(audio_file_path, "rb") as audio_file:
                try:
                    # 구 버전 API 호출 (0.28.1)
                    response = openai.Audio.transcribe(
                        model="whisper-1",
                        file=audio_file,
                        language="ko",
                        response_format="verbose_json"
                    )
                except Exception as e:
                    print(f"API 호출 중 오류: {e}")
                    raise
                    
            print("전사 완료")
            
            # 응답 형식 변환 (0.28.1 버전에서는 응답이 딕셔너리 형태)
            class TranscriptionResponse:
                def __init__(self, data):
                    self.text = data.get('text', '')
                    self.segments = []
                    for seg in data.get('segments', []):
                        segment = type('Segment', (), {})
                        segment.start = seg.get('start', 0)
                        segment.end = seg.get('end', 0)
                        segment.text = seg.get('text', '')
                        self.segments.append(segment)
            
            return TranscriptionResponse(response)
        except Exception as e:
            print(f"전사 중 오류 발생: {e}")
            raise
    
    @staticmethod
    def summarize_text(text, summary_type="paragraph"):
        """
        ChatGPT API를 사용하여 텍스트 요약을 생성합니다.
        
        Args:
            text (str): 요약할 텍스트
            summary_type (str): 요약 유형 ('paragraph' 또는 'timestamped')
            
        Returns:
            str: 요약된 텍스트
        """
        try:
            # 새로운 요약 프롬프트
            new_prompt = """
            당신은 회의록이나 강의 내용을 이해하고 요약하는 데 특화된 **전문 AI 비서**입니다. 사용자로부터 음성 인식으로 추출된 긴 텍스트를 전달받으면, **내용의 진행 순서(타임라인)**에 따라 **상세하고 체계적인 요약**을 만듭니다.

            다음 지침을 따르십시오:

            - 요약은 원본보다 간결하게 하되 **가능한 한 상세하고 길게** 작성하세요. 핵심과 관련 없는 잡담이나 의미 없는 부분은 제외하고, **주요 논의 내용은 모두 포함**하십시오.
            - **시간 흐름에 따라** 요약을 정리하세요. 발언이 있었던 **시각 또는 순서**를 밝혀가며, 해당 구간에서 논의된 핵심 내용을 서술하세요. (예: "`00:15 -` 팀장 인사 및 회의 목표 소개...")
            - 특히 **중요 결정사항**, **핵심 주장/논거**, 그리고 **주요 질문과 그 답변**은 놓치지 말고 요약에 포함하세요. 어떤 결정이 나왔을 경우 **`결정:`** 이라고 표시하고 내용을 밝히세요. 중요한 질문이 오갔다면 **질문과 답변을 함께** 정리하세요.
            - 최종 요약은 **한국어**로 작성하세요. 읽기 쉽도록 항목별로 나열하고, 필요한 경우 문장부호나 강조(**굵게** 등)를 활용해 핵심을 돋보이게 하십시오.
            - 정보는 **주어진 자료에 근거해서만** 요약하세요. 원문에 없었던 내용은 추측하거나 만들어내지 말고, 언급되지 않은 사항은 요약에서도 언급하지 않습니다.
            
            전사 내용:
            """
            
            prompt = ""
            if summary_type == "paragraph":
                prompt = f"{new_prompt}\n{text}"
            elif summary_type == "timestamped":
                prompt = f"{new_prompt}\n{text}"
            
            try:
                # 구 버전 API 호출 (0.28.1)
                response = openai.ChatCompletion.create(
                    model="o3-mini", # o3-mini 모델로 변경
                    messages=[
                        {"role": "system", "content": "당신은 회의록이나 강의 내용을 이해하고 요약하는 데 특화된 전문 AI 비서입니다."},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=8000 # max_tokens를 max_completion_tokens로 변경
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"API 호출 중 오류: {e}")
                # o3-mini 모델 호출 실패 시 gpt-3.5-turbo로 대체
                print("o3-mini 모델 호출 실패, gpt-3.5-turbo로 대체합니다.")
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "당신은 회의록이나 강의 내용을 이해하고 요약하는 데 특화된 전문 AI 비서입니다."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
                return response.choices[0].message.content
                
        except Exception as e:
            print(f"요약 중 오류 발생: {e}")
            raise 
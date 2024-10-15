import os
import azure.cognitiveservices.speech as speechsdk
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
import tkinter as tk
from tkinter import filedialog, messagebox
import time

def recognize_from_video(video_path, start_time, end_time):
    # 処理が始まる前にchunkフォルダを削除し、空の状態から始める
    chunk_dir = "chunks"
    if os.path.exists(chunk_dir):
        for file_name in os.listdir(chunk_dir):
            file_path = os.path.join(chunk_dir, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(chunk_dir)
    os.makedirs(chunk_dir, exist_ok=True)

    # 動画ファイルの長さを取得
    video = VideoFileClip(video_path)
    video_duration = video.duration

    # 終了時間が動画の長さを超えないように調整
    if end_time > video_duration:
        end_time = video_duration

    # 動画ファイルから音声を抽出
    video = video.subclip(start_time, end_time)
    audio_path = "extracted_audio.wav"
    video.audio.write_audiofile(audio_path)

    # 音声ファイルを読み込む
    audio = AudioSegment.from_wav(audio_path)
    chunk_length_ms = 10000  # 10秒ごとに分割
    chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]

    # Azure Speech SDKの設定
    speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('AZURE_SPEECH_KEY'), region="japaneast")
    speech_config.speech_recognition_language="ja-JP"

    full_transcript = ""

    for i, chunk in enumerate(chunks):
        chunk_path = os.path.join(chunk_dir, f"chunk_{i}.wav")
        chunk.export(chunk_path, format="wav")
        audio_config = speechsdk.audio.AudioConfig(filename=chunk_path)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        print(f"Processing chunk {i + 1}/{len(chunks)}...")
        speech_recognition_result = speech_recognizer.recognize_once_async().get()

        if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
            full_transcript += speech_recognition_result.text + " "
        elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
            print(f"No speech could be recognized in chunk {i + 1}: {speech_recognition_result.no_match_details}")
        elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_recognition_result.cancellation_details
            print(f"Speech Recognition canceled in chunk {i + 1}: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print(f"Error details: {cancellation_details.error_details}")
                print("Did you set the speech resource key and region values?")

    print("Full Transcript:")
    print(full_transcript)

    # 議事録をoutputフォルダに保存
    save_transcript(full_transcript)

    # 作成したファイルをすべて削除
    cleanup_files(audio_path, chunk_dir)

def save_transcript(transcript):
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "transcript.txt")
    
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(transcript)
    
    print(f"Transcript saved to {output_file}")

def cleanup_files(audio_path, chunk_dir):
    # 変換したwavファイルを削除
    if os.path.exists(audio_path):
        while True:
            try:
                os.remove(audio_path)
                break
            except PermissionError:
                time.sleep(1)
    
def select_file():
    file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4;*.avi;*.mov;*.mkv")])
    if file_path:
        entry_file_path.delete(0, tk.END)
        entry_file_path.insert(0, file_path)

def start_transcription():
    video_path = entry_file_path.get()
    start_time = float(entry_start_time.get())
    end_time = float(entry_end_time.get())
    if not video_path:
        messagebox.showerror("Error", "Please select a video file.")
        return
    recognize_from_video(video_path, start_time, end_time)

# GUIの設定
root = tk.Tk()
root.title("Video Transcription")

tk.Label(root, text="Video File:").grid(row=0, column=0, padx=10, pady=10)
entry_file_path = tk.Entry(root, width=50)
entry_file_path.grid(row=0, column=1, padx=10, pady=10)
tk.Button(root, text="Browse", command=select_file).grid(row=0, column=2, padx=10, pady=10)

tk.Label(root, text="Start Time (seconds):").grid(row=1, column=0, padx=10, pady=10)
entry_start_time = tk.Entry(root, width=20)
entry_start_time.grid(row=1, column=1, padx=10, pady=10)

tk.Label(root, text="End Time (seconds):").grid(row=2, column=0, padx=10, pady=10)
entry_end_time = tk.Entry(root, width=20)
entry_end_time.grid(row=2, column=1, padx=10, pady=10)

tk.Button(root, text="Start Transcription", command=start_transcription).grid(row=3, column=1, padx=10, pady=20)

root.mainloop()

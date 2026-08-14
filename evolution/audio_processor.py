"""
Audio Processing Module for QB Protocol
Handles real microphone access, audio recording, speech-to-text, and text-to-speech
with proper permission handling and user consent.
"""

import subprocess
import json
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import time


class AudioProcessor:
    """Real-time audio processing with microphone access and voice synthesis."""
    
    def __init__(self):
        self.permission_granted = False
        self.audio_commands = {
            'macos': {
                'record': 'afrecord',
                'play': 'afplay',
                'speak': 'say',
            },
            'linux': {
                'record': 'arecord',
                'play': 'aplay',
                'speak': 'espeak',
            }
        }
        
    def get_platform(self) -> str:
        """Detect current platform."""
        import platform
        system = platform.system().lower()
        if system == 'darwin':
            return 'macos'
        elif system == 'linux':
            return 'linux'
        else:
            return 'unknown'
    
    def request_microphone_permission(self) -> bool:
        """Request microphone permission from user."""
        if self.permission_granted:
            return True
            
        # Check if we can at least do text-to-speech
        platform = self.get_platform()
        commands = self.audio_commands.get(platform, {})
        
        if not commands:
            print(f"Platform {platform} not supported")
            return False
        
        # Check if speak command is available
        speak_cmd = commands.get('speak')
        if speak_cmd:
            try:
                subprocess.run(['which', speak_cmd], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                print(f"Text-to-speech command {speak_cmd} not found")
                return False
        
        # Request user permission
        print("Audio access requested for voice processing.")
        print("This will allow the system to:")
        print("- Generate voice responses using system text-to-speech")
        print("- Record your voice (if recording commands are available)")
        print("- Extract voice characteristics for personalization")
        
        response = input("Grant audio permission? (yes/no): ").lower()
        
        if response == 'yes':
            self.permission_granted = True
            print("Audio permission granted")
            return True
        else:
            print("Audio permission denied")
            return False
    
    def record_audio(self, duration: float = 5.0, output_file: str = "recording.wav") -> bool:
        """Record audio from microphone for specified duration."""
        if not self.permission_granted:
            print("Audio permission not granted")
            return False
        
        platform = self.get_platform()
        commands = self.audio_commands.get(platform, {})
        
        if platform == 'macos':
            try:
                # Use afrecord for macOS
                cmd = [
                    'afrecord',
                    '-t', 'wav',
                    '-f', 'WAVE',
                    '-d', str(duration),
                    output_file
                ]
                subprocess.run(cmd, check=True)
                print(f"Audio recorded to {output_file}")
                return True
            except Exception as e:
                print(f"Recording not available (afrecord may not be installed): {e}")
                print("You can still use text-to-speech functionality")
                return False
        elif platform == 'linux':
            try:
                # Use arecord for Linux
                cmd = [
                    'arecord',
                    '-d', str(int(duration)),
                    '-f', 'cd',
                    '-r', '44100',
                    output_file
                ]
                subprocess.run(cmd, check=True)
                print(f"Audio recorded to {output_file}")
                return True
            except Exception as e:
                print(f"Recording not available (arecord may not be installed): {e}")
                print("You can still use text-to-speech functionality")
                return False
        else:
            print("Platform not supported for recording")
            print("You can still use text-to-speech functionality")
            return False
    
    def speak_text(self, text: str, voice: Optional[str] = None) -> bool:
        """Convert text to speech and play it."""
        if not self.permission_granted:
            print("Audio permission not granted")
            return False
        
        platform = self.get_platform()
        commands = self.audio_commands.get(platform, {})
        
        if platform == 'macos':
            try:
                cmd = ['say', text]
                if voice:
                    cmd.extend(['-v', voice])
                subprocess.run(cmd, check=True)
                print(f"Spoken: {text}")
                return True
            except Exception as e:
                print(f"Error speaking text: {e}")
                return False
        elif platform == 'linux':
            try:
                cmd = ['espeak', text]
                subprocess.run(cmd, check=True)
                print(f"Spoken: {text}")
                return True
            except Exception as e:
                print(f"Error speaking text: {e}")
                return False
        else:
            print("Platform not supported for text-to-speech")
            return False
    
    def play_audio(self, audio_file: str) -> bool:
        """Play audio file."""
        if not Path(audio_file).exists():
            print(f"Audio file not found: {audio_file}")
            return False
        
        platform = self.get_platform()
        commands = self.audio_commands.get(platform, {})
        
        if platform == 'macos':
            try:
                cmd = ['afplay', audio_file]
                subprocess.run(cmd, check=True)
                print(f"Playing: {audio_file}")
                return True
            except Exception as e:
                print(f"Error playing audio: {e}")
                return False
        elif platform == 'linux':
            try:
                cmd = ['aplay', audio_file]
                subprocess.run(cmd, check=True)
                print(f"Playing: {audio_file}")
                return True
            except Exception as e:
                print(f"Error playing audio: {e}")
                return False
        else:
            print("Platform not supported for audio playback")
            return False
    
    def get_audio_info(self, audio_file: str) -> Optional[Dict[str, Any]]:
        """Get information about audio file."""
        if not Path(audio_file).exists():
            print(f"Audio file not found: {audio_file}")
            return None
        
        try:
            # Use ffprobe if available, otherwise provide basic info
            try:
                cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', audio_file]
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                info = json.loads(result.stdout)
                return info
            except:
                # Fallback to basic file info
                file_size = Path(audio_file).stat().st_size
                return {
                    'file_size': file_size,
                    'format': 'unknown',
                    'duration': 'unknown',
                }
        except Exception as e:
            print(f"Error getting audio info: {e}")
            return None
    
    def simulate_voice_extraction(self, audio_file: str) -> Dict[str, Any]:
        """Simulate voice feature extraction (placeholder for real implementation)."""
        if not Path(audio_file).exists():
            print(f"Audio file not found: {audio_file}")
            return {}
        
        # This is a placeholder - real implementation would use libraries like librosa
        # For now, we return simulated features
        return {
            'mfcc_features': [[0.0] * 13 for _ in range(100)],
            'chroma_features': [[0.0] * 12 for _ in range(50)],
            'spectral_contrast': [[0.0] * 7 for _ in range(50)],
            'pitch_mean': 150.0,
            'duration': 5.0,
            'voice_characteristics': {
                'pitch': 150.0,
                'timbre': 0.5,
                'tempo': 1.0,
                'resonance': 0.5,
                'articulation': 0.5,
            }
        }


# Global audio processor instance
audio_processor = AudioProcessor()


def test_audio_processing():
    """Test audio processing functionality."""
    print("Testing Audio Processing Module")
    print("=" * 50)
    
    # Request permission
    if not audio_processor.request_microphone_permission():
        print("Permission denied. Exiting test.")
        return
    
    # Test text to speech (should work on macOS)
    print("\n1. Testing text to speech...")
    if audio_processor.speak_text("Hello, this is a test of the voice system. You should hear this message."):
        print("Text-to-speech successful")
    else:
        print("Text-to-speech failed")
    
    # Test recording (may not work without afrecord)
    print("\n2. Testing audio recording...")
    if audio_processor.record_audio(duration=3.0, output_file="test_recording.wav"):
        print("Recording successful")
        
        # Get audio info
        print("\n3. Testing audio info...")
        info = audio_processor.get_audio_info("test_recording.wav")
        if info:
            print(f"Audio info: {json.dumps(info, indent=2)}")
        
        # Test playback
        print("\n4. Testing audio playback...")
        audio_processor.play_audio("test_recording.wav")
        
        # Test voice extraction (simulated)
        print("\n5. Testing voice feature extraction...")
        features = audio_processor.simulate_voice_extraction("test_recording.wav")
        print(f"Features extracted: {list(features.keys())}")
    else:
        print("Recording not available (this is normal without afrecord)")
        print("You can still use text-to-speech functionality")
    
    print("\nTest complete")


if __name__ == "__main__":
    test_audio_processing()

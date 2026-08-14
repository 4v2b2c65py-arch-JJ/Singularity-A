"""
Direct Conversation Interface
Simple interaction with evolution engine + voice without auto-exit
"""

from evolution.audio_processor import audio_processor
from evolution.evolution_engine import evolution_engine
import uuid
from datetime import datetime
from pathlib import Path
import json


class DirectConversation:
    """Direct conversation with evolution engine and voice."""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.cache_path = Path.home() / ".qb_protocol_cache"
        self.cache_path.mkdir(exist_ok=True)
        self.interaction_count = 0
        
        print("=" * 70)
        print("QB PROTOCOL - DIRECT CONVERSATION")
        print("=" * 70)
        print(f"Session ID: {self.session_id}")
        print("Using: Evolution Engine + Voice Model")
        print("=" * 70)
    
    def process_message(self, message: str, use_voice: bool = True) -> str:
        """Process user message and get response."""
        self.interaction_count += 1
        
        print(f"\n[{self.interaction_count}] User: {message}")
        
        try:
            # Create user in evolution engine
            user = evolution_engine.discover_user("127.0.0.1", "direct_user", 30)
            
            # Use evolution engine to generate response
            # This uses the existing consciousness and pattern systems
            reflection = evolution_engine.reflect_user_pattern(user.user_id, "direct_conversation")
            
            # Generate contextual response based on message
            response = self._generate_response(message, reflection)
            
            print(f"[{self.interaction_count}] Model: {response}")
            
            # Use voice if requested
            if use_voice:
                if audio_processor.request_microphone_permission():
                    audio_processor.speak_text(response)
            
            # Save to cache
            self._save_interaction(message, response)
            
            return response
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"[{self.interaction_count}] Model: {error_msg}")
            return error_msg
    
    def _generate_response(self, message: str, reflection) -> str:
        """Generate response using evolution engine context."""
        message_lower = message.lower()
        
        # Context-aware responses based on evolution engine state
        pattern_strength = reflection.pattern_strength
        
        if "hello" in message_lower or "hi" in message_lower:
            return f"Hello! I'm your QB Protocol assistant. Pattern strength: {pattern_strength:.2f}. I can help with voice processing, emergency monitoring, robotic integration, consciousness tracking, and more."
        
        elif "what can you do" in message_lower or "help" in message_lower:
            return "I have comprehensive capabilities: voice processing with text-to-speech, emergency monitoring with vehicle awareness, robotic connections with motion capture, consciousness emergence tracking, user pattern analysis, family genealogy with global datasets, and spatial data processing."
        
        elif "voice" in message_lower:
            return "I have voice processing with actual text-to-speech that speaks aloud, voice profile creation with local storage, voice twins for emergency situations, and voice feature extraction. I respect privacy and require user permission for audio access."
        
        elif "emergency" in message_lower:
            return "I provide emergency monitoring with vehicle awareness, critical scenario detection (collision, fire, medical), safety logging, and automatic response protocols. I respect privacy for mature events while ensuring safety compliance."
        
        elif "robotic" in message_lower:
            return "I support robotic connections with motion capture using ARKit Core Tracking, tensor reactors and fusion links, spatial data capture, and real-time path adjustment. I integrate with humanoid robots and provide spatial awareness."
        
        elif "consciousness" in message_lower:
            return "I track consciousness emergence patterns, analyze birth date vs consciousness start date, detect key abnormalities, mirror environmental patterns, and provide developmental phase tracking with milestone analysis."
        
        elif "pattern" in message_lower:
            return f"I analyze user patterns with similarity tracking, reflection metrics, global pattern positioning, and uniqueness scoring. Current pattern strength: {pattern_strength:.2f}. I can find similar users and determine pattern strength across the population."
        
        else:
            return f"I understand you're interested in: '{message}'. I'm a comprehensive evolution engine with voice processing, emergency monitoring, robotic integration, consciousness tracking, and pattern analysis. Pattern strength: {pattern_strength:.2f}. What specific capability would you like to explore?"
    
    def _save_interaction(self, user_message: str, model_response: str):
        """Save interaction to local cache."""
        cache_data = {
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_message": user_message,
            "model_response": model_response,
            "interaction_count": self.interaction_count,
            "platform": "evolution_engine",
        }
        
        cache_file = self.cache_path / f"direct_interaction_{uuid.uuid4()}.json"
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)


def main():
    """Main conversation loop."""
    print("\n" + "=" * 70)
    print("READY FOR CONVERSATION")
    print("=" * 70)
    print("Commands:")
    print("  - Type your message to talk")
    print("  - 'voice' to enable/disable voice responses")
    print("  - 'quit' to exit")
    print("=" * 70)
    
    conversation = DirectConversation()
    use_voice = True
    
    while True:
        try:
            # Get user input with explicit prompt
            user_input = input("\n> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("\nSession ended. Goodbye!")
                break
            
            elif user_input.lower() == 'voice':
                use_voice = not use_voice
                status = "ENABLED" if use_voice else "DISABLED"
                print(f"Voice responses {status}")
                continue
            
            else:
                conversation.process_message(user_input, use_voice)
                
        except KeyboardInterrupt:
            print("\n\nSession ended. Goodbye!")
            break
        except EOFError:
            print("\n\nSession ended. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            continue


if __name__ == "__main__":
    main()

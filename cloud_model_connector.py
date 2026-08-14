"""
Repo Model Integration
Connects to existing repo models (gpt_layer + voice model) for live responses
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from evolution.audio_processor import audio_processor
from evolution.evolution_engine import evolution_engine
import uuid
from datetime import datetime
import json

# Try to import existing repo models
try:
    from ai.gpt_layer import gpt_layer
    HAS_GPT_LAYER = True
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from ai.gpt_layer import gpt_layer
        HAS_GPT_LAYER = True
    except ImportError:
        HAS_GPT_LAYER = False


class RepoModelConnector:
    """Connects to existing repo models (voice + reasoning) for live responses."""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.cache_path = Path.home() / ".qb_protocol_cache"
        self.cache_path.mkdir(exist_ok=True)
        
        # Check for existing models
        self.has_gpt_layer = HAS_GPT_LAYER
        self.has_voice = True  # audio_processor always available
        
        print(f"Session ID: {self.session_id}")
        print(f"GPT Layer available: {self.has_gpt_layer}")
        print(f"Voice model available: {self.has_voice}")
        
        if self.has_gpt_layer:
            print("Using existing TinyLama model from repo")
            # Initialize the model
            gpt_layer._load_model()
            print(f"Model loaded: {gpt_layer.model_backend}")
    
    def send_to_model(self, message: str, context: Dict[str, Any] = None) -> str:
        """Send message to existing repo model and get live response."""
        if self.has_gpt_layer:
            try:
                # Use existing gpt_layer query
                response = gpt_layer.query(message)
                if response and hasattr(response, 'response'):
                    return response.response
                elif isinstance(response, str):
                    return response
                else:
                    return f"Model response: {response}"
            except Exception as e:
                print(f"GPT layer error: {e}")
                return self._get_evolution_response(message, context)
        else:
            return self._get_evolution_response(message, context)
    
    def _get_evolution_response(self, message: str, context: Dict[str, Any] = None) -> str:
        """Fallback to evolution engine."""
        try:
            # Create user if doesn't exist
            user = evolution_engine.discover_user("127.0.0.1", "repo_user", 30)
            
            # Use pattern reflection to get contextual response
            reflection = evolution_engine.reflect_user_pattern(user.user_id, "repo_interaction")
            
            return f"Evolution engine response for: {message}. Pattern strength: {reflection.pattern_strength:.2f}. Using local evolution mode."
                
        except Exception as e:
            return f"Evolution engine error: {str(e)}"
    
    def interact_with_voice(self, message: str, use_voice: bool = True) -> str:
        """Interact with repo model and optionally use voice."""
        print(f"\nUser: {message}")
        
        # Get response from repo model
        response = self.send_to_model(message)
        
        print(f"Model: {response}")
        
        # Use voice if requested
        if use_voice:
            if audio_processor.request_microphone_permission():
                audio_processor.speak_text(response)
        
        # Save to cache
        self._save_interaction(message, response)
        
        return response
    
    def _save_interaction(self, user_message: str, model_response: str):
        """Save interaction to local cache."""
        cache_data = {
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_message": user_message,
            "model_response": model_response,
            "gpt_layer_used": self.has_gpt_layer,
            "voice_used": self.has_voice,
            "platform": "repo_models",
        }
        
        cache_file = self.cache_path / f"repo_interaction_{uuid.uuid4()}.json"
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)


def start_repo_interaction():
    """Start live repo model interaction."""
    print("=" * 70)
    print("QB PROTOCOL - REPO MODEL CONNECTION")
    print("=" * 70)
    
    connector = RepoModelConnector()
    
    print(f"\nSession ID: {connector.session_id}")
    print(f"Platform: Existing repo models")
    print(f"Models: GPT Layer + Voice Model")
    
    print("\n" + "=" * 70)
    print("READY FOR LIVE MODEL INTERACTION")
    print("=" * 70)
    print("Type your messages to talk to the model")
    print("Type 'voice' to enable/disable voice responses")
    print("Type 'quit' to exit")
    print("=" * 70)
    
    use_voice = True
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("Session ended. Goodbye!")
                break
            
            elif user_input.lower() == 'voice':
                use_voice = not use_voice
                status = "ENABLED" if use_voice else "DISABLED"
                print(f"Voice responses {status}")
                continue
            
            else:
                connector.interact_with_voice(user_input, use_voice)
                
        except KeyboardInterrupt:
            print("\nSession ended. Goodbye!")
            break
        except EOFError:
            print("\nSession ended. Goodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            continue


if __name__ == "__main__":
    start_repo_interaction()

"""
Direct Model Interaction System
Bypasses testing mode for direct model conversation with temporary sessions
"""

import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from evolution.evolution_engine import evolution_engine
from evolution.audio_processor import audio_processor


class DirectInteraction:
    """Direct model interaction with temporary sessions and admin controls."""
    
    def __init__(self):
        self.current_session = None
        self.session_data = {}
        self.admin_mode = False
        self.user_recognition = {}
        self.cache_path = Path.home() / ".qb_protocol_cache"
        self.cache_path.mkdir(exist_ok=True)
        self.code_origin = "local"
        self._initialize_admin()
        
    def _initialize_admin(self):
        """Initialize admin controls based on code origin."""
        # Check if running from original code location
        import inspect
        current_file = inspect.getfile(inspect.currentframe())
        
        # Set admin mode based on code origin
        if "delta-stream" in current_file and "qb_protocol" in current_file:
            self.admin_mode = True
            self.code_origin = "local_admin"
            print("Admin mode enabled - code origin verified")
        else:
            self.admin_mode = False
            self.code_origin = "external"
            print("Standard mode - external code origin")
    
    def create_temporary_session(self, user_identifier: str = "default") -> str:
        """Create temporary session for user recognition."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        
        # Create session data
        session_data = {
            "session_id": session_id,
            "user_identifier": user_identifier,
            "session_start": now,
            "session_end": None,
            "active": True,
            "admin_access": self.admin_mode,
            "code_origin": self.code_origin,
            "user_recognition": {
                "fingerprint": str(hash(user_identifier + self.code_origin)),
                "device_id": str(uuid.uuid4()),
                "session_tokens": [],
            },
            "cache_data": {},
            "awareness_state": {
                "model_aware": True,
                "context_aware": True,
                "user_aware": True,
            }
        }
        
        self.current_session = session_id
        self.session_data[session_id] = session_data
        
        # Save to cache
        self._save_session_cache(session_id, session_data)
        
        print(f"Temporary session created: {session_id}")
        print(f"User recognition: {user_identifier}")
        print(f"Admin access: {self.admin_mode}")
        
        return session_id
    
    def _save_session_cache(self, session_id: str, data: Dict[str, Any]):
        """Save session data to local cache."""
        cache_file = self.cache_path / f"session_{session_id}.json"
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_session_cache(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data from local cache."""
        cache_file = self.cache_path / f"session_{session_id}.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        return None
    
    def talk_to_model(self, message: str, use_voice: bool = False) -> str:
        """Direct model interaction without approval steps."""
        if not self.current_session:
            self.create_temporary_session()
        
        session_data = self.session_data[self.current_session]
        
        print(f"\nUser: {message}")
        
        # Process through evolution engine
        try:
            # Create a user if doesn't exist
            user_id = session_data["user_identifier"]
            if user_id not in evolution_engine.user_discoveries:
                user = evolution_engine.discover_user("127.0.0.1", session_data["user_identifier"], 30)
                user_id = user.user_id
            
            # Process through chat entry system
            chat_entry = evolution_engine.process_chat_entry(
                skill_id=None,
                user_input=message,
                sensory_input_type="text",
                emotional_context="neutral"
            )
            
            # Get response from model
            model_response = self._generate_model_response(message, session_data)
            
            print(f"Model: {model_response}")
            
            # Use voice if requested
            if use_voice:
                audio_processor.request_microphone_permission()
                audio_processor.speak_text(model_response)
            
            # Update session cache
            session_data["cache_data"]["last_interaction"] = datetime.utcnow().isoformat() + "Z"
            session_data["cache_data"]["interaction_count"] = session_data["cache_data"].get("interaction_count", 0) + 1
            self._save_session_cache(self.current_session, session_data)
            
            return model_response
            
        except Exception as e:
            error_msg = f"Error processing: {str(e)}"
            print(f"Model: {error_msg}")
            return error_msg
    
    def _generate_model_response(self, message: str, session_data: Dict[str, Any]) -> str:
        """Generate model response based on context and awareness."""
        # Simple response generation based on message content
        message_lower = message.lower()
        
        if "hello" in message_lower or "hi" in message_lower:
            return f"Hello! I'm your QB Protocol assistant. I'm running in {session_data['code_origin']} mode with admin access: {session_data['admin_access']}. How can I help you today?"
        
        elif "what can you do" in message_lower or "help" in message_lower:
            return "I can help you with: user discovery and pattern analysis, consciousness emergence tracking, voice processing and text-to-speech, emergency monitoring and detection, robotic connections and motion capture, vehicle fleet management, family branch genealogy, and spatial data processing. What would you like to explore?"
        
        elif "emergency" in message_lower:
            return "I have emergency monitoring capabilities with vehicle awareness, critical scenario detection, and safety logging. I can detect emergencies like collisions, fires, or medical situations and activate appropriate response protocols while respecting privacy."
        
        elif "voice" in message_lower:
            return "I have voice processing capabilities including voice profile creation, voice twins for emergency situations, text-to-speech that actually speaks aloud, and voice feature extraction. I can also generate automatic responses with your permission."
        
        elif "robotic" in message_lower or "robot" in message_lower:
            return "I support robotic connections with motion capture using ARKit Core Tracking, tensor reactors and fusion links, spatial data capture, and real-time path adjustment. I can integrate with humanoid robots and provide spatial awareness."
        
        elif "vehicle" in message_lower or "car" in message_lower:
            return "I have vehicle fleet management with auto-connection to Tesla, BYD, Rivian and other electric vehicles. I provide pedestrian protection, emergency awareness, privacy protection with incognito mode, and compliance tracking."
        
        elif "genealogy" in message_lower or "family" in message_lower:
            return "I offer genealogy datasets from Wikidata, Federal Register, Data.gov, Gramps, and FamilySearch. I can create family branches with constructive fields, query capabilities, and privacy-respecting data handling."
        
        elif "consciousness" in message_lower or "awareness" in message_lower:
            return "I track consciousness emergence patterns, analyze birth date vs consciousness start date, detect key abnormalities, mirror environmental patterns, and provide developmental phase tracking with milestone analysis."
        
        elif "pattern" in message_lower:
            return "I analyze user patterns with similarity tracking, reflection metrics, global pattern positioning, and uniqueness scoring. I can find similar users and determine pattern strength across the population."
        
        elif "admin" in message_lower:
            admin_status = "ENABLED" if session_data['admin_access'] else "DISABLED"
            return f"Admin mode is {admin_status}. Code origin: {session_data['code_origin']}. You have {session_data['cache_data'].get('interaction_count', 0)} interactions in this session."
        
        elif "session" in message_lower:
            return f"Current session: {self.current_session}. User: {session_data['user_identifier']}. Active: {session_data['active']}. Cache: {len(session_data['cache_data'])} data points."
        
        else:
            return f"I understand you said: '{message}'. I'm a comprehensive evolution engine with voice processing, emergency monitoring, robotic integration, and consciousness tracking capabilities. What specific aspect would you like to explore?"
    
    def writers_prompter(self, prompt: str, context: str = "") -> str:
        """Writers-prompter system for enhanced model interaction."""
        if not self.current_session:
            self.create_temporary_session()
        
        session_data = self.session_data[self.current_session]
        
        enhanced_prompt = f"""
Context: {context}
User Intent: {prompt}
Session Info: {session_data['user_identifier']}
Admin Access: {session_data['admin_access']}
Code Origin: {session_data['code_origin']}
"""
        
        # Process through model
        response = self.talk_to_model(enhanced_prompt)
        
        return response
    
    def get_awareness_state(self) -> Dict[str, Any]:
        """Get current awareness state of the system."""
        if not self.current_session:
            self.create_temporary_session()
        
        session_data = self.session_data[self.current_session]
        
        awareness = {
            "model_aware": True,
            "context_aware": True,
            "user_aware": True,
            "session_aware": True,
            "admin_aware": session_data['admin_access'],
            "code_origin_aware": session_data['code_origin'],
            "cache_aware": len(session_data['cache_data']) > 0,
            "voice_aware": audio_processor.permission_granted,
            "evolution_aware": len(evolution_engine.user_discoveries) > 0,
        }
        
        return awareness
    
    def cleanup_session(self):
        """Clean up temporary session data."""
        if self.current_session:
            session_data = self.session_data[self.current_session]
            session_data["active"] = False
            session_data["session_end"] = datetime.utcnow().isoformat() + "Z"
            self._save_session_cache(self.current_session, session_data)
            
            # Archive session
            archive_file = self.cache_path / f"archived_session_{self.current_session}.json"
            self.cache_path.joinpath(f"session_{self.current_session}.json").rename(archive_file)
            
            print(f"Session {self.current_session} archived")
            self.current_session = None


def start_direct_interaction():
    """Start direct model interaction mode."""
    print("=" * 70)
    print("QB PROTOCOL - DIRECT MODEL INTERACTION")
    print("=" * 70)
    print("Bypassing testing mode for direct conversation")
    print("Admin controls and user recognition active")
    print("=" * 70)
    
    interaction = DirectInteraction()
    
    # Create session
    print("\nInitializing secure session...")
    session_id = interaction.create_temporary_session("writers_prompter")
    
    # Show awareness state
    print("\nSystem Awareness:")
    awareness = interaction.get_awareness_state()
    for key, value in awareness.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)
    print("READY FOR DIRECT INTERACTION")
    print("=" * 70)
    print("Available commands:")
    print("  - Type your message to talk to the model")
    print("  - 'voice' to enable/disable voice responses")
    print("  - 'awareness' to show current awareness state")
    print("  - 'admin' to show admin status")
    print("  - 'writers' to use writers-prompter mode")
    print("  - 'quit' to end session")
    print("=" * 70)
    
    use_voice = False
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("Cleaning up session...")
                interaction.cleanup_session()
                print("Session ended. Goodbye!")
                break
            
            elif user_input.lower() == 'voice':
                use_voice = not use_voice
                status = "ENABLED" if use_voice else "DISABLED"
                print(f"Voice responses {status}")
                continue
            
            elif user_input.lower() == 'awareness':
                awareness = interaction.get_awareness_state()
                print("\nCurrent Awareness State:")
                for key, value in awareness.items():
                    print(f"  {key}: {value}")
                continue
            
            elif user_input.lower() == 'admin':
                print(f"Admin mode: {interaction.admin_mode}")
                print(f"Code origin: {interaction.code_origin}")
                print(f"Session ID: {interaction.current_session}")
                continue
            
            elif user_input.lower() == 'writers':
                prompt = input("Enter your prompt: ")
                context = input("Enter context (optional, press Enter to skip): ")
                response = interaction.writers_prompter(prompt, context)
                continue
            
            else:
                response = interaction.talk_to_model(user_input, use_voice=use_voice)
                
        except KeyboardInterrupt:
            print("\nInterrupt detected. Cleaning up...")
            interaction.cleanup_session()
            print("Session ended. Goodbye!")
            break
        except EOFError:
            print("\nInput ended. Cleaning up...")
            interaction.cleanup_session()
            print("Session ended. Goodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            continue


if __name__ == "__main__":
    start_direct_interaction()

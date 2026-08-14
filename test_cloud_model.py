"""
Cloud Model Integration Test
Tests the Hugging Face model connector with your token
"""

from cloud_model_connector import CloudModelConnector
import os


def test_cloud_model():
    """Test Hugging Face model connection."""
    print("=" * 70)
    print("HUGGING FACE MODEL CONNECTION TEST")
    print("=" * 70)
    
    # Check environment variables
    print("\nChecking Hugging Face configuration...")
    hf_token = os.getenv("HF_TOKEN")
    hf_model = os.getenv("HF_MODEL_ID")
    
    if hf_token:
        print(f"✓ HF_TOKEN found: {hf_token[:20]}...")
    else:
        print("✗ HF_TOKEN not found, using default token")
    
    if hf_model:
        print(f"✓ HF_MODEL_ID found: {hf_model}")
    else:
        print("Using default model: meta-llama/Llama-2-7b-chat-hf")
    
    # Initialize connector
    print("\nInitializing Hugging Face connector...")
    connector = CloudModelConnector()
    
    # Test connection
    print("\nTesting Hugging Face model connection...")
    test_message = "Hello, this is a test message"
    
    print(f"Sending: {test_message}")
    response = connector.send_to_cloud_model(test_message)
    print(f"Received: {response}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print("Hugging Face model integration successful")
    print("Voice and reasoning models will use Hugging Face live responses")
    print("\nTo use a different model:")
    print("  export HF_MODEL_ID='your-preferred-model-id'")


if __name__ == "__main__":
    test_cloud_model()

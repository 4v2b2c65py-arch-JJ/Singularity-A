#!/usr/bin/env python3
"""
QB Protocol - Telecom Package
SIM/SMS/voice service with multi-provider support.
"""

from .phone.validator import PhoneValidator, PhoneInfo, phone_validator
from .sms.providers import SMSProvider, SMSMessage, SMSAdapter, sms_adapter
from .voice.webrtc import WebRTCManager, WebRTCSession, webrtc_manager
from .otp.manager import OTPManager, OTPCode, otp_manager
from .privacy.architecture import PrivacyManager, PrivacyConfig, privacy_manager
from .api.routes import router as telecom_router

__all__ = [
    "PhoneValidator",
    "PhoneInfo",
    "phone_validator",
    "SMSProvider",
    "SMSMessage",
    "SMSAdapter",
    "sms_adapter",
    "WebRTCManager",
    "WebRTCSession",
    "webrtc_manager",
    "OTPManager",
    "OTPCode",
    "otp_manager",
    "PrivacyManager",
    "PrivacyConfig",
    "privacy_manager",
    "telecom_router",
]

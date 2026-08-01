import pytest
from app.services.router import route_message
from app.schemas.message import RoutingResult

def test_empty_message_mutes():
    msg = {
        "message_id": "test_1",
        "user_id": "user_1",
        "message_text": "",
        "media_type": "",
    }
    result = route_message(msg)
    assert isinstance(result, RoutingResult)
    assert result.action == "mute"
    assert result.route_method == "fast_path"

def test_otp_scam_mutes():
    msg = {
        "message_id": "test_2",
        "user_id": "user_1",
        "message_text": "Verify your account. OTP is 1234",
    }
    result = route_message(msg)
    assert isinstance(result, RoutingResult)
    assert result.action == "mute"
    assert result.message_type == "scam"
    assert result.route_method == "fast_path"

def test_direct_mention_notifies():
    msg = {
        "message_id": "test_3",
        "user_id": "user_1",
        "message_text": "Hey @user_1, check this out!",
    }
    result = route_message(msg)
    assert isinstance(result, RoutingResult)
    assert result.action == "notify"
    assert result.message_type == "personal"
    assert result.route_method == "fast_path"

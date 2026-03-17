from ta_bot.models.signal import Signal

def test_signal_model():
    signal = Signal(
        strategy_id="test_strat",
        symbol="BTCUSDT",
        action="buy",
        confidence=0.8,
        current_price=50000.0,
        price=50000.0
    )
    assert signal.strategy_id == "test_strat"
    assert signal.action == "buy"
    
    data = signal.to_dict()
    assert data["strategy_id"] == "test_strat"
    assert data["strategy"] == "test_strat" # Should be same as strategy_id if not provided
    assert "timestamp" in data

if __name__ == "__main__":
    test_signal_model()
    print("Signal model test passed!")

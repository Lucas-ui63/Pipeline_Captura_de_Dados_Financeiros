import pytest
from unittest.mock import patch
from main import Request

def test_request_config_load():
    """Testa se a classe Request carrega as configurações corretamente."""
    req = Request()
    assert 'period' in req.config
    assert 'interval' in req.config
    assert 'ticker' in req.config

@patch('yfinance.download')
def test_request_data_returns_json(mock_yf_download):
    """Testa a extração usando mock para não depender da internet."""
   
    import pandas as pd
    mock_df = pd.DataFrame({'Close': [5.50, 5.60]}, index=pd.to_datetime(['2026-01-01', '2026-01-02']))
    mock_yf_download.return_value = mock_df
    req = Request()
    resultado_json = req.request_data('EURBRL=X')
    assert resultado_json is not None
    assert isinstance(resultado_json, str)
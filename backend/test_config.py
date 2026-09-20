import os
import pytest
from unittest.mock import patch

def test_missing_env_vars_raises_value_error():
    """
    Test that our critical modules raise a ValueError if required
    environment variables are missing.
    """
    with patch.dict(os.environ, {}, clear=True):
        # Test auth.py
        with pytest.raises(ValueError, match="SECRET_KEY environment variable is missing"):
            import importlib
            import auth
            importlib.reload(auth)

        # Test database.py
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DATABASE_URL environment variable is missing"):
                import importlib
                import database
                importlib.reload(database)

        # Test graph/nodes.py
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GROQ_API_KEY environment variable is missing"):
                import importlib
                import graph.nodes
                importlib.reload(graph.nodes)
            
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-groq-key"}, clear=True):
            with pytest.raises(ValueError, match="RESEND_API_KEY environment variable is missing"):
                import importlib
                import graph.nodes
                importlib.reload(graph.nodes)

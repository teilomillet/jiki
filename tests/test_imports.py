# Basic smoke test to ensure jiki can be imported and Jiki factory is available

def test_imports():
    import jiki
    # The Jiki factory function should exist and be callable
    assert hasattr(jiki, 'Jiki'), "jiki.Jiki should be present"
    from jiki import Jiki
    assert callable(Jiki), "Jiki should be callable" 
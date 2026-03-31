import os
import unittest
from src.core.settings import settings

class TestConfig(unittest.TestCase):
    def test_default_models(self):
        # We mapped ResearchAgent to nvidia in config.yaml
        self.assertEqual(settings.get_agent_llm("Research Agent"), "nvidia")
        
        # We mapped SystemAgent to ollama/llama3.2 in config.yaml
        self.assertEqual(settings.get_agent_llm("System Agent"), "ollama/llama3.2")
        
        # We mapped GeneralAgent to gemini/gemini-2.0-flash in config.yaml
        self.assertEqual(settings.get_agent_llm("General Agent"), "gemini/gemini-2.0-flash")

    def test_router_model(self):
        self.assertEqual(settings.router_llm, "ollama")

    def test_timeouts(self):
        self.assertIsInstance(settings.cloud_timeout, int)
        self.assertIsInstance(settings.local_timeout, int)

if __name__ == '__main__':
    unittest.main()

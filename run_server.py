#!/usr/bin/env python3
"""
Launcher per DeepPrint Pro WebSocket Server.
Esegui da: python run_server.py
"""
import sys
import os
from pathlib import Path

# Configura il sys.path per evitare conflitti con il built-in 'platform'
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Rimuovi temporaneamente dalla sys.path qualsiasi percorso che potrebbe
# contenere un 'platform' directory (non necessario con questa struttura)
# Ora esegui il server

if __name__ == '__main__':
    # Import diretto da file, bypassa il sistema di package
    import importlib.util

    server_path = PROJECT_ROOT / "platform" / "ws_server.py"
    spec = importlib.util.spec_from_file_location("ws_server", server_path)
    module = importlib.util.module_from_spec(spec)
    
    # Inietta PROJECT_ROOT nel modulo prima di eseguirlo
    module.PROJECT_ROOT = PROJECT_ROOT
    
    spec.loader.exec_module(module)
    module.main()

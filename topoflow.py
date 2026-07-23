#!/usr/bin/env python
"""TopoFlow CLI 入口。"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from src.main import main

if __name__ == "__main__":
    sys.exit(main())

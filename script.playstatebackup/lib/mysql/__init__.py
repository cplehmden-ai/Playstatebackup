import os
import sys

__path__ = [os.path.dirname(__file__)]

# Make the bundled package addressable as the top-level mysql package during
# runtime imports. This keeps the addon independent from a system installation.
if "mysql" not in sys.modules:
    sys.modules["mysql"] = sys.modules[__name__]

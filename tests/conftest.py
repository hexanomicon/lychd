import logging

# 1. Silence the noisy libs using standard logging
logging.getLogger("faker").setLevel(logging.WARNING)

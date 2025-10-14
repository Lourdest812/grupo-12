from . import models

# real_estate/__init__.py
import os, logging
_logger = logging.getLogger(__name__)
_logger.warning("REAL_ESTATE cargado desde: %s", os.path.abspath(os.path.dirname(__file__)))

from . import models  # lo que ya tenías

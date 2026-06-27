"""Data-ingest layer: Excel loaders for the URS workbook + the corporate-bond universe
pipeline.

Named ``dataio`` rather than ``io`` on purpose — the repo's root ``conftest.py`` inserts
``src/`` at ``sys.path[0]``, so a package literally named ``io`` would shadow the standard
library ``io`` that pandas / openpyxl import internally.
"""

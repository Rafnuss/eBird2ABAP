"""Convert eBird observations to auditable atlas-card candidates."""

from importlib.metadata import version

from .ebird2card import (
    DEFAULT_EBD_DIR, ebird2abap, download_EBD, iter_EBD, read_EBD,
    load_avilist_mapping, ebd2chk, chk2valid_card, checkday_pentad_observer,
    valid_card2chk_card, chk_card2card_chk, chk_card2ebd_f_u, ebd_f_u2card_exp,
)
from .pentad import latlng2pentad, pentad2latlng, pentad2polygon, latlng2polygon, generate_pentad_grid
from .taxonomy import TaxonomyMatchError, add_avilist_taxonomy, check_taxonomy_updates, load_taxonomy_bundle, update_taxonomy
from .reporting import generate_report

__version__ = version('eBird2ABAP')
__all__ = [
    '__version__', 'DEFAULT_EBD_DIR', 'ebird2abap', 'download_EBD', 'iter_EBD', 'read_EBD',
    'load_avilist_mapping', 'ebd2chk', 'chk2valid_card', 'checkday_pentad_observer',
    'valid_card2chk_card', 'chk_card2card_chk', 'chk_card2ebd_f_u', 'ebd_f_u2card_exp',
    'latlng2pentad', 'pentad2latlng', 'pentad2polygon', 'latlng2polygon', 'generate_pentad_grid',
    'TaxonomyMatchError', 'add_avilist_taxonomy', 'check_taxonomy_updates', 'load_taxonomy_bundle', 'update_taxonomy',
    'generate_report',
]

"""Execute committed notebook defaults on offline synthetic data.

Run: uv run --group notebooks python tests/check_notebooks.py
Outputs remain in temporary storage; source notebooks stay output-free.
"""

from pathlib import Path
import tempfile

import nbformat
from nbclient import NotebookClient

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='ebird-notebook-check-') as directory:
    for path in sorted((root / 'notebook').glob('*.ipynb')):
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        client = NotebookClient(notebook, timeout=180, kernel_name='python3',
                                resources={'metadata': {'path': str(root)}})
        client.execute()
        nbformat.write(notebook, Path(directory) / path.name)
        print(f'PASS {path.name}: all code cells executed', flush=True)

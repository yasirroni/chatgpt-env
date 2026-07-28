# Bundle outputs

Generated bundles are published as GitHub Release assets.
They are not committed to the repository.

A Julia environment bundle contains:

```text
julia-env-<environment>/
├── environment/
│   ├── Project.toml
│   └── Manifest.toml
├── depot/
├── BUNDLE_INFO.toml
└── VALIDATION.txt
```

The semantic-search Python environment bundle contains:

```text
semantic-search/
├── wheels/
├── models/
│   └── sentence-transformers/
│       └── all-MiniLM-L6-v2/
├── BUNDLE_INFO.toml
├── VALIDATION.txt
└── SHA256SUMS
```

Julia bundles are published as `.tar.zst` files.
The semantic-search bundle is published as `semantic-search-linux-x86_64-py313.zip`.
Every archive has a matching `.sha256` checksum file.

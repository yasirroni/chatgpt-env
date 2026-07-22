# Bundle outputs

Generated Julia environment archives are published as GitHub Release assets.
They are not committed to the repository.

A bundle contains:

```text
julia-env-<environment>/
├── environment/
│   ├── Project.toml
│   └── Manifest.toml
├── depot/
├── BUNDLE_INFO.toml
└── VALIDATION.txt
```

All archives are published as single `.tar.zst` files with a matching `.sha256`
checksum file.

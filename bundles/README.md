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

Archives below 512 MiB are published as one `.tar.zst` file. Larger archives
are split into parts below the ChatGPT per-file limit, with reconstruction and
checksum metadata published beside them.

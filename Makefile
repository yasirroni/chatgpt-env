.PHONY: validate

validate:
	python3 scripts/validate_repository.py
	bash -n scripts/build_environment.sh
	bash -n scripts/build_runtime_bundle.sh
	bash -n scripts/publish_release.sh

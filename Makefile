.PHONY: validate

validate:
	python3 scripts/validate_repository.py
	python3 -m py_compile scripts/build_python_environment.py
	bash -n scripts/build_environment.sh
	bash -n scripts/build_runtime_bundle.sh
	bash -n scripts/publish_release.sh

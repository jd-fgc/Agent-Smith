UV = uv run --active python
PIP = $(if $(wildcard $(VENV_PIP)), $(VENV_PIP), pip)
MYPY_FLAGS= --warn-return-any --warn-unused-ignores --ignore-missing-imports \
		--disallow-untyped-defs --check-untyped-defs \
		--explicit-package-bases


define step
	@printf "$(1)"; \
	out="$$( { $(2); } 2>&1 )"; \
	status="$$?"; \
	if [ "$$status" -eq 0 ]; then \
	printf "$(GREEN) $(1) $(RESET)\n"; \
	else \
	printf "$(RED) $(1) $(RESET)\n"; \
	printf "\n$$out\n\n"; \
	exit $$status; \
	fi
endef


all: install

install:
	./package_installation.sh

run:
	@uv run python -m src

debug:
	@$(UV) -m pdb main.py

clean:
		@echo "$(RED) Cleaning...$(RESET)"
		@find . -type d -name "pycache" -exec rm -rf {} +
		@find . -type f -name "*.pyc" -delete
		@rm -rf .mypy_cache
		@rm -rf .pytest_cache
		@rm -rf .coverage

lint:
	$(call step,Looking for flake8 error,flake8 student/src/)
	$(call step,Looking for mypy error,mypy student/src/ $(MYPY_FLAGS))

lint-strict:
	$(call step,Looking for flake8 error,flake8 --exclude=data/ .)
	$(call step,Looking for mypy strict error,mypy student/src $(MYPY_FLAGS))



.PHONY: all install run debug lint lint-strict
.SILENT:

RESET=\033[0m
RED=\033[1;31m
BLUE=\033[1;34m
GREEN=\033[1;32m
YELLOW=\032[1;33m
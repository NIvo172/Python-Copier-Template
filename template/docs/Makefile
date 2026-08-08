PYTHON ?= python

.PHONY: help all html coverage clean

help:
	@echo "Documentation targets:"
	@echo "  all       Build HTML and validate API documentation coverage"
	@echo "  html      Build HTML documentation"
	@echo "  coverage  Build and validate API documentation coverage"
	@echo "  clean     Remove generated documentation files"

all html coverage clean:
	@$(PYTHON) ../scripts/build_docs.py $@

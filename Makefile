.PHONY: install test dev clean

VENV ?= .venv

dev:
	$(VENV)/bin/pip install -e '.[dev]'

test:
	$(VENV)/bin/pytest

install:
	install -d $(DESTDIR)/usr/local/bin
	install -d $(DESTDIR)/usr/local/share/call-cleaner
	install -d $(DESTDIR)/usr/local/lib/call-cleaner
	install -m 755 bin/cleaner $(DESTDIR)/usr/local/bin/cleaner
	install -m 755 share/wrapper.sh $(DESTDIR)/usr/local/share/call-cleaner/wrapper.sh
	install -m 755 share/wrapper-purge.sh $(DESTDIR)/usr/local/share/call-cleaner/wrapper-purge.sh
	cp -r src/call_cleaner $(DESTDIR)/usr/local/lib/call-cleaner/

clean:
	rm -rf build dist *.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +

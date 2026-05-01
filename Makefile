.PHONY: install install-termux test dev clean release

VENV ?= .venv
DESTDIR ?=
PREFIX ?= /data/data/com.termux/files/usr

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

install-termux:
	install -d $(DESTDIR)$(PREFIX)/bin
	install -d $(DESTDIR)$(PREFIX)/share/call-cleaner
	install -d $(DESTDIR)$(PREFIX)/lib/call-cleaner
	install -m 755 bin/cleaner $(DESTDIR)$(PREFIX)/bin/cleaner
	install -m 755 share/wrapper.sh $(DESTDIR)$(PREFIX)/share/call-cleaner/wrapper.sh
	install -m 755 share/wrapper-purge.sh $(DESTDIR)$(PREFIX)/share/call-cleaner/wrapper-purge.sh
	cp -r src/call_cleaner $(DESTDIR)$(PREFIX)/lib/call-cleaner/

release:
	@if [ -z "$(VERSION)" ]; then echo "set VERSION=x.y.z"; exit 1; fi
	sed -i 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml
	sed -i 's/^__version__ = ".*"/__version__ = "$(VERSION)"/' src/call_cleaner/__init__.py
	git commit -am "release: v$(VERSION)"
	git tag -a v$(VERSION) -m "v$(VERSION)"
	git push origin main --tags

clean:
	rm -rf build dist *.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
